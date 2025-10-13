# backend/exams/views_api.py
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

# ------- TEACHER --------
class TeacherPendingRequests(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestSerializer

    def get_queryset(self):
        return Request.objects.filter(tusername=self.request.user.username, status="Pending").order_by("-id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class TeacherAcceptedRequests(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RequestSerializer

    def get_queryset(self):
        return Request.objects.filter(tusername=self.request.user.username).exclude(status="Pending").order_by("-id")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def TeacherAcceptRequest(request, req_id):
    r = Request.objects.filter(id=req_id, tusername=request.user.username).first()
    if not r:
        return Response({"detail": "Not found"}, status=404)
    r.status = "Accepted"
    r.save()
    return Response({"message": "Accepted"})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def TeacherRejectRequest(request, req_id):
    r = Request.objects.filter(id=req_id, tusername=request.user.username).first()
    if not r:
        return Response({"detail": "Not found"}, status=404)
    r.status = "Rejected"
    r.save()
    return Response({"message": "Rejected"})

class TeacherUploadPaper(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, req_id):
        r = Request.objects.filter(id=req_id, tusername=request.user.username).first()
        if not r:
            return Response({"detail": "Request not found"}, status=404)
        if r.status not in ("Accepted",):
            return Response({"detail": "Upload allowed only for Accepted requests"}, status=400)

        paper = request.FILES.get("paper")
        if not paper:
            return Response({"detail": "paper is required"}, status=400)

        # write to temp file and encrypt
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

        # upload encrypted file to IPFS
        res = add_file(enc_path)
        cid = res["Hash"]

        # RSA-encrypt metadata and save teacher private key file to Request.private_key
        arr = a_encryption(cid, key, request.user.teacher_id)
        priv_path = os.path.join(settings.ENCRYPTION_ROOT, f"{request.user.teacher_id}_private_key.pem")
        with open(priv_path, "rb") as pf:
            r.private_key.save(os.path.basename(priv_path), File(pf), save=True)

        r.enc_field = arr
        r.status = "Uploaded"
        r.save()

        # try record on blockchain
        try:
            record_cid(r.s_code, cid)
        except Exception:
            pass

        # cleanup
        try: os.remove(enc_path)
        except: pass
        try: os.remove(tmp_path)
        except: pass

        return Response({"message": "Uploaded", "cid": cid}, status=201)

class TeacherMyFinalPapers(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FinalPaperSerializer

    def get_queryset(self):
        user = self.request.user
        return FinalPapers.objects.filter(subject=user.subject, branch=user.branch, semester=user.semester, course=user.course).order_by("-id")

# -------- COE -----------
# ------- COE -----------

class COEListRequests(generics.ListAPIView):
    """
    Return all active (non-finalized) requests for COE dashboard.
    Active = Pending, Accepted, Uploaded (but not finalized).
    """
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        reqs = Request.objects.filter(status__in=["Pending", "Accepted", "Uploaded"]).order_by("-id")
        response_data = []
        for r in reqs:
            try:
                u = User.objects.get(username=r.tusername)
                first_name = u.first_name
                last_name = u.last_name
            except User.DoesNotExist:
                first_name = ""
                last_name = ""
            response_data.append({
                "id": r.id,
                "s_code": r.s_code,
                "tusername": r.tusername,
                "teacher_first_name": first_name,
                "teacher_last_name": last_name,
                "status": r.status,
                "deadline": r.deadline,
            })
        return Response(response_data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def COEGetTeachers(request):
    """
    Returns teachers available for request.
    Exclude only those with active requests (Pending, Accepted, Uploaded).
    Also return subject code and default syllabus/q_pattern URLs (if configured on SubjectCode).
    """
    course = request.data.get('course')
    semester = request.data.get('semester')
    branch = request.data.get('branch')
    subject = request.data.get('subject')

    if not (course and semester and branch and subject):
        return Response({"detail": "course, semester, branch, subject are required"}, status=400)

    sqs = SubjectCode.objects.filter(subject=subject).values()
    if not sqs:
        return Response({"detail": "Subject not found in codes"}, status=404)
    s_code = sqs[0]['s_code']

    # Exclude only teachers with active requests (Pending, Accepted, Uploaded)
    active_tusernames = list(
        Request.objects.filter(s_code=s_code, status__in=["Pending", "Accepted", "Uploaded"])
        .values_list('tusername', flat=True)
        .distinct()
    )

    uploaded_ids = list(Request.objects.filter(s_code=s_code, status='Uploaded').values('id'))

    queryset = User.objects.filter(
        course=course, semester=semester, branch=branch, subject=subject
    ).exclude(username__in=active_tusernames).values(
        'id', 'username', 'first_name', 'last_name', 'teacher_id'
    )

    # get default files from SubjectCode if available
    default_syllabus_url = None
    default_q_pattern_url = None
    subj_obj = SubjectCode.objects.filter(s_code=s_code).first()
    if subj_obj:
        try:
            if subj_obj.syllabus:
                try:
                    default_syllabus_url = request.build_absolute_uri(subj_obj.syllabus.url)
                except Exception:
                    default_syllabus_url = subj_obj.syllabus.url
            if subj_obj.q_pattern:
                try:
                    default_q_pattern_url = request.build_absolute_uri(subj_obj.q_pattern.url)
                except Exception:
                    default_q_pattern_url = subj_obj.q_pattern.url
        except Exception:
            default_syllabus_url = None
            default_q_pattern_url = None

    return Response({
        'teachers': list(queryset),
        's_code': s_code,
        'uploaded_request_ids': uploaded_ids,
        'default_syllabus_url': default_syllabus_url,
        'default_q_pattern_url': default_q_pattern_url
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def COEAddTeacher(request):
    """
    Create a Request for a teacher.
    Behavior:
    - If frontend sends syllabus/q_pattern files in request.FILES, use them.
    - Otherwise, attempt to use default files stored in SubjectCode for the s_code.
    """
    s_code = request.data.get('s_code')
    syllabus_file = request.FILES.get('syllabus')  # optional
    q_pattern_file = request.FILES.get('q_pattern')  # optional
    t_id = request.data.get('g_id')
    deadline = request.data.get('deadline')
    total_marks = request.data.get('total_marks')

    if not (s_code and t_id and deadline):
        return Response({"detail":"missing fields"}, status=400)

    u = User.objects.filter(id=t_id).values('username')
    if not u:
        return Response({"detail":"teacher not found"}, status=404)
    username = u[0]['username']

    # If no files are provided in request, try to fetch from SubjectCode defaults
    subj_obj = SubjectCode.objects.filter(s_code=s_code).first()
    if (not syllabus_file or not q_pattern_file):
        if not subj_obj:
            return Response({"detail":"Subject code not found"}, status=404)
        # if files missing, use defaults if available
        if not syllabus_file and subj_obj.syllabus:
            syllabus_file = subj_obj.syllabus
        if not q_pattern_file and subj_obj.q_pattern:
            q_pattern_file = subj_obj.q_pattern

    # after this, both files must be present
    if not (syllabus_file and q_pattern_file):
        return Response({"detail":"syllabus and q_pattern files are required (either upload or configure defaults for subject code)"}, status=400)

    obj = Request.objects.create(
        tusername=username,
        s_code=s_code,
        syllabus=syllabus_file,
        q_pattern=q_pattern_file,
        deadline=deadline,
        status="Pending",
        total_marks=int(total_marks) if total_marks is not None else 100
    )
    new_teacher = User.objects.filter(username=username).values()
    return Response({'new_teacher': list(new_teacher), 'request_id': obj.id}, status=201)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def COECandidates(request):
    """
    Returns anonymized list of uploaded requests for given s_code.
    Only returns Uploaded requests, and de-duplicates by teacher (keeps latest Upload per teacher).
    Query param: ?s_code=CSE501
    Response: [{id, teacher_username, teacher_name, paper_number, status, deadline, total_marks, syllabus_url, q_pattern_url}, ...]
    """
    s_code = request.query_params.get("s_code")
    if not s_code:
        return Response({"detail":"s_code query param required"}, status=400)

    uploaded_qs = Request.objects.filter(s_code=s_code, status='Uploaded').order_by("id")
    if not uploaded_qs.exists():
        return Response({"detail":"No uploaded candidates for this s_code"}, status=404)

    # Deduplicate by teacher username: keep the latest uploaded request per teacher (highest id)
    latest_by_teacher = {}
    for r in uploaded_qs:
        # overwrite so the highest-id stays
        latest_by_teacher[r.tusername] = r

    candidates_list = sorted(latest_by_teacher.values(), key=lambda x: x.id)

    response = []
    for idx, r in enumerate(candidates_list):
        try:
            u = User.objects.get(username=r.tusername)
            tname = f"{u.first_name} {u.last_name}".strip()
        except User.DoesNotExist:
            tname = r.tusername
        response.append({
            "id": r.id,
            "teacher_username": r.tusername,
            "teacher_name": tname,
            "paper_number": f"Paper {idx+1}",
            "status": r.status,
            "deadline": r.deadline,
            "total_marks": r.total_marks,
            "syllabus_url": r.syllabus.url if r.syllabus else None,
            "q_pattern_url": r.q_pattern.url if r.q_pattern else None,
        })
    return Response(response)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def COEFinalize(request, req_id):
    req = Request.objects.filter(id=req_id).first()
    if not req:
        return Response({"detail":"Not found"}, status=404)
    if req.status != "Uploaded":
        return Response({"detail":"Only Uploaded requests can be finalized"}, status=400)

    # decrypt metadata and fetch from IPFS
    values = a_decryption([req.enc_field, req.private_key])
    key = values[0]
    cid = values[1].decode("utf-8")
    enc_bytes = get_file(cid)

    class _R:
        def __init__(self, b): self.text = b.decode("latin1")
    rfake = _R(enc_bytes)
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

    # delete other candidate requests for same s_code (we keep the selected req and mark finalized)
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
@permission_classes([IsAuthenticated])
def SuperintendentGetDecryptInfo(request, paper_id):
    fp = FinalPapers.objects.filter(id=paper_id).first()
    if not fp: return Response({"detail": "Not found"}, status=404)
    return Response({
        "s_code": fp.s_code,
        "paper_url": fp.paper.url if fp.paper else None
    })
