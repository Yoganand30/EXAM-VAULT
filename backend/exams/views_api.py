from django.contrib.auth import authenticate, get_user_model
from django.core.files import File
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import *
from .models import *
from .encryption import encrypt_file, decrypt_file
from .a_encryption import a_encryption, a_decryption
from .ipfs_utils import add_file, get_file
from .blockchain import record_cid

import os
import tempfile

User = get_user_model()

def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}

# -------- AUTH ----------
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    ser = RegisterSerializer(data=request.data)
    if ser.is_valid():
        user = ser.save()
        return Response({"message": "Registered", "username": user.username}, status=201)
    return Response(ser.errors, status=400)

@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = authenticate(username=ser.validated_data["username"], password=ser.validated_data["password"])
    if not user:
        return Response({"detail": "Invalid credentials"}, status=401)
    t = _tokens_for_user(user)
    return Response({"tokens": t, "role": user.role, "username": user.username})

# ------- COMMON ---------
class SubjectCodeList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = SubjectCode.objects.all()
    serializer_class = SubjectCodeSerializer

# ------- TEACHER (original dashboard: Pending + Accepted/Uploaded) --------
class TeacherPendingRequests(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestSerializer
    def get_queryset(self):
        return Request.objects.filter(tusername=self.request.user.username, status="Pending").order_by("-id")

class TeacherAcceptedRequests(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestSerializer
    def get_queryset(self):
        # everything except Pending (Accepted, Uploaded, Finalized)
        return Request.objects.filter(tusername=self.request.user.username).exclude(status="Pending").order_by("-id")

@api_view(["POST"])
def TeacherAcceptRequest(request, req_id):
    r = Request.objects.filter(id=req_id, tusername=request.user.username).first()
    if not r:
        return Response({"detail": "Not found"}, status=404)
    r.status = "Accepted"
    r.save()
    return Response({"message": "Accepted"})

class TeacherUploadPaper(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    def post(self, request, req_id):
        r = Request.objects.filter(id=req_id, tusername=request.user.username).first()
        if not r: 
            return Response({"detail": "Request not found"}, status=404)
        if r.status not in ("Accepted",):
            return Response({"detail": "Upload allowed only for Accepted requests"}, status=400)

        # 1) Encrypt uploaded file with Fernet
        paper = request.FILES.get("paper")
        if not paper: 
            return Response({"detail":"paper is required"}, status=400)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            for chunk in paper.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            class _F:
                def __init__(self, fobj, name): self._f, self._n = fobj, name
                def read(self): return self._f.read()
                def __str__(self): return os.path.basename(self._n)
            key = encrypt_file(_F(f, paper.name))

        enc_path = os.path.join(settings.ENCRYPTION_ROOT, f"{paper.name}.encrypted")

        # 2) Upload encrypted file to IPFS
        res = add_file(enc_path)   # {'Name':..., 'Hash':...}
        cid = res["Hash"]

        # 3) Encrypt metadata with RSA and save teacher private key
        arr = a_encryption(cid, key, request.user.teacher_id)
        priv_path = os.path.join(settings.ENCRYPTION_ROOT, f"{request.user.teacher_id}_private_key.pem")
        with open(priv_path, "rb") as pf:
            r.private_key.save(os.path.basename(priv_path), File(pf), save=True)
        r.enc_field = arr
        r.status = "Uploaded"
        r.save()

        # 4) Record on blockchain
        txhash = record_cid(r.s_code, cid)

        try: os.remove(enc_path)
        except: pass
        try: os.remove(tmp_path)
        except: pass

        return Response({"message": "Uploaded", "cid": cid, "tx": txhash}, status=201)

# -------- COE (original behaviour) -----------
class COEListRequests(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestSerializer
    def get_queryset(self):
        return Request.objects.all().order_by("-id")

@api_view(["POST"])
def COEGetTeachers(request):
    """
    Original flow:
      - POST with course, semester, branch, subject
      - returns: available teachers (excluding already requested), corresponding subject code,
                 and list of request ids already Uploaded for that subject code.
    """
    course = request.data.get('course')
    semester = request.data.get('semester')
    branch = request.data.get('branch')
    subject = request.data.get('subject')

    if not (course and semester and branch and subject):
        return Response({"detail": "course, semester, branch, subject are required"}, status=400)

    # Teachers already requested
    queryset1 = Request.objects.values('tusername').distinct()

    # Subject code for selected subject
    sqs = SubjectCode.objects.filter(subject=subject).values()
    if not sqs:
        return Response({"detail": "Subject not found in codes"}, status=404)
    s_code = sqs[0]['s_code']

    # Requests that are already uploaded for this subject code (to help COE pick finalize later)
    queryset2 = Request.objects.filter(s_code=s_code, status='Uploaded').values('id')

    # Eligible teachers (exclude those already in a Request)
    queryset = User.objects.filter(
        course=course, semester=semester, branch=branch, subject=subject
    ).exclude(username__in=[q['tusername'] for q in queryset1]).values(
        'id', 'username', 'first_name', 'last_name', 'teacher_id'
    )

    return Response({
        'teachers': list(queryset),
        's_code': s_code,
        'uploaded_request_ids': list(queryset2)
    })

@api_view(["POST"])
def COEAddTeacher(request):
    """
    Original add_teacher:
      - s_code, syllabus(file), q_pattern(file), g_id (teacher id), deadline
      - creates a Request with status Pending for that teacher
    """
    s_code = request.data.get('s_code')
    syllabus = request.FILES.get('syllabus')
    q_pattern = request.FILES.get('q_pattern')
    t_id = request.data.get('g_id')
    deadline = request.data.get('deadline')

    if not (s_code and syllabus and q_pattern and t_id and deadline):
        return Response({"detail":"missing fields"}, status=400)

    u = User.objects.filter(id=t_id).values('username')
    if not u:
        return Response({"detail":"teacher not found"}, status=404)
    username = u[0]['username']

    obj = Request.objects.create(
        tusername=username,
        s_code=s_code,
        syllabus=syllabus,
        q_pattern=q_pattern,
        deadline=deadline,
        status="Pending"
    )
    new_teacher = User.objects.filter(username=username).values()
    return Response({'new_teacher': list(new_teacher), 'request_id': obj.id}, status=201)

@api_view(["POST"])
def COEFinalize(request, req_id):
    """
    Choose one Uploaded request for a subject code, decrypt from IPFS and store FinalPapers.
    Also delete the other requests with same s_code (like original).
    """
    req = Request.objects.filter(id=req_id).first()
    if not req:
        return Response({"detail":"Not found"}, status=404)
    if req.status != "Uploaded":
        return Response({"detail":"Only Uploaded requests can be finalized"}, status=400)

    # 1) RSA -> (key, cid)
    values = a_decryption([req.enc_field, req.private_key])
    key = values[0]
    cid = values[1].decode("utf-8")

    # 2) Encrypted bytes from IPFS
    enc_bytes = get_file(cid)

    # 3) Prepare Response-like object for decrypt_file()
    class _R:
        def __init__(self, b): self.text = b.decode("latin1")
    rfake = _R(enc_bytes)

    # 4) Decrypt -> PDF and save
    pdf_file = decrypt_file(rfake, key, req.s_code)

    teacher = User.objects.filter(username=req.tusername).values("course","semester","branch","subject")[0]
    final = FinalPapers.objects.create(
        s_code=req.s_code,
        course=teacher["course"],
        semester=teacher["semester"],
        branch=teacher["branch"],
        subject=teacher["subject"],
    )
    final.paper.save(f"{req.s_code}.pdf", pdf_file, save=True)

    # Keep only this request; remove others for same s_code
    Request.objects.filter(s_code=req.s_code).exclude(id=req.id).delete()
    req.status = "Finalized"
    req.save()

    return Response({"message": "Finalized", "paper_id": final.id})

# ----- SUPERINTENDENT -----
class SuperintendentListFinal(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FinalPaperSerializer
    queryset = FinalPapers.objects.all().order_by("-id")

@api_view(["GET"])
def SuperintendentGetDecryptInfo(request, paper_id):
    fp = FinalPapers.objects.filter(id=paper_id).first()
    if not fp: return Response({"detail": "Not found"}, status=404)
    return Response({
        "s_code": fp.s_code,
        "paper_url": fp.paper.url if fp.paper else None
    })
