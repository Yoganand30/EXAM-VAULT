from django.urls import path
from . import views_api as v

urlpatterns = [
    # Auth
    path("register/", v.register_user),
    path("login/", v.login_user),

    # Common
    path("subject-codes/", v.SubjectCodeList.as_view()),

    # Teacher (split just like the original dashboard)
    path("teacher/requests/pending/", v.TeacherPendingRequests.as_view()),
    path("teacher/requests/accepted/", v.TeacherAcceptedRequests.as_view()),
    path("teacher/requests/<int:req_id>/accept/", v.TeacherAcceptRequest),
    path("teacher/requests/<int:req_id>/upload/", v.TeacherUploadPaper.as_view()),

    # COE (original flow)
    path("coe/requests/", v.COEListRequests.as_view()),
    path("coe/teachers/", v.COEGetTeachers),          # filter + list available teachers
    path("coe/requests/add/", v.COEAddTeacher),        # create request for a teacher (with files)
    path("coe/requests/<int:req_id>/finalize/", v.COEFinalize),

    # Superintendent (unchanged)
    path("sup/final-papers/", v.SuperintendentListFinal.as_view()),
    path("sup/final-papers/<int:paper_id>/decrypt-info/", v.SuperintendentGetDecryptInfo),
]
