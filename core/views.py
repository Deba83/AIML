from django.shortcuts import render  # type: ignore
from django.http import JsonResponse  # type: ignore
from django.views.decorators.csrf import csrf_exempt  # type: ignore
from .forms import EligibilityForm  # type: ignore
from .models import Scheme  # type: ignore
import json
import datetime
import logging

logger = logging.getLogger(__name__)

from .services.data_pipeline import create_scheme_safe

# Eligibility engine imports
from .services.matcher import get_best_schemes

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.generic import TemplateView

from .services.undo_service import undo_last_action

@csrf_exempt
def add_scheme(request):
    """
    Unified Endpoint for API + Browser Tester.
    GET: Returns HTML form.
    POST: Processes data (JSON or Form) with Undo tracking.
    """
    if request.method == 'GET':
        return render(request, 'core/add_scheme_form.html')

    if request.method != 'POST':
        return JsonResponse({'success': False, 'errors': {'method': 'Only GET/POST allowed'}}, status=405)

    # Support both JSON (API) and Form Data (Browser)
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        elif 'data' in request.POST:
            data = json.loads(request.POST['data'])
        else:
            data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'errors': {'json': 'Invalid JSON format'}}, status=400)

    result = create_scheme_safe(data)
    if result['success']:
        return JsonResponse(result, status=201)
    else:
        return JsonResponse(result, status=400)

class UndoAPIView(APIView):
    """
    Reverse the last database action.
    """
    def post(self, request, *args, **kwargs):
        success, message = undo_last_action()
        if success:
            return Response({'success': True, 'message': message}, status=status.HTTP_200_OK)
        else:
            return Response({'success': False, 'errors': {'system': message}}, status=status.HTTP_400_BAD_REQUEST)


# ==============================
# VIEWS
# ==============================

def check_eligibility(request):
    if request.method == 'POST':
        form = EligibilityForm(request.POST)
        if form.is_valid():
            edu_str = form.cleaned_data['education_level']

            # Marks normalisation
            if edu_str in ['ug', 'pg']:
                cgpa = form.cleaned_data.get('cgpa_ug') or form.cleaned_data.get('cgpa_pg') or 0
                marks = cgpa * 10
            else:
                marks = form.cleaned_data.get(f'marks_{edu_str}') or 0

            user = {
                "education_level":     edu_str,
                "income":    form.cleaned_data['income'],
                "age":       form.cleaned_data['age'],
                "category":  form.cleaned_data['category'],
                "gender":    form.cleaned_data.get('gender', ''),
                "state":     form.cleaned_data['state'],
                "is_disabled": form.cleaned_data['is_disabled'],
                "documents": get_user_documents(form.cleaned_data),
                "marks":     marks,
            }

            all_schemes = Scheme.objects.all()
            total_fetched = all_schemes.count()

            logger.info(
                "ELIGIBILITY CHECK | edu=%s income=%s category=%s state=%s marks=%s",
                edu_str, user['income'], user['category'], user['state'], user['marks']
            )
            print(
                f"DEBUG-INPUT | edu={edu_str}, income={user['income']}, "
                f"cat={user['category']}, state={user['state']}, marks={user['marks']}"
            )

            # Fix user dictionary keys for matcher
            user['available_documents'] = user.pop('documents', [])

            from core.services.matcher import get_best_schemes
            matched_schemes = get_best_schemes(user, all_schemes)

            today = datetime.date.today()
            results = []
            for m in matched_schemes:
                # Deadline classification
                is_expired = False
                is_expiring_soon = m.get("is_expiring_soon", False)
                dl_str = m.get("deadline", "")
                if dl_str:
                    try:
                        dl = datetime.datetime.strptime(dl_str, "%Y-%m-%d").date()
                        is_expired = dl < today
                    except ValueError:
                        pass

                results.append({
                    "name":              m['scheme'],
                    "type":              m['type'],
                    "provider":          m['provider'],
                    "score":             m['score'],
                    "reasons":           m['reasons'],
                    "missing_documents": m['missing_documents'],
                    "status":            m['status'],
                    "deadline":          dl_str,
                    "is_expired":        is_expired,
                    "is_expiring_soon":  is_expiring_soon,
                    "source":            m['source'],
                    "description":       m['description'],
                    "benefits":          m['benefits'],
                })

            # Debug summary
            print(
                f"DEBUG-SUMMARY | fetched={total_fetched}, "
                f"matched={len(results)}, rejected={total_fetched - len(results)}"
            )

            def group_results(results_list):
                return {
                    "schemes":      [r for r in results_list if r['type'] == 'scheme'],
                    "scholarships": [r for r in results_list if r['type'] == 'scholarship'],
                    "internships":  [r for r in results_list if r['type'] == 'internship'],
                    "fellowships":  [r for r in results_list if r['type'] == 'fellowship'],
                }

            no_results = len(results) == 0

            context = {
                "govt":         group_results([r for r in results if r['provider'] == 'govt']),
                "private":      group_results([r for r in results if r['provider'] == 'private']),
                "ngo":          group_results([r for r in results if r['provider'] == 'ngo']),
                "govt_count":   len([r for r in results if r['provider'] == 'govt']),
                "private_count": len([r for r in results if r['provider'] == 'private']),
                "ngo_count":    len([r for r in results if r['provider'] == 'ngo']),
                "user_data":    user,
                "total_fetched": total_fetched,
                "total_matched": len(results),
                "no_results":   no_results,
                "no_results_message": (
                    "Based on your exact profile, no schemes matched all eligibility criteria."
                    if no_results else ""
                ),
            }
            return render(request, 'core/result.html', context)
    else:
        form = EligibilityForm()

    return render(request, 'core/form.html', {'form': form})


def get_user_documents(data):
    docs = []
    mapping = {
        'aadhaar':       'Aadhaar',
        'income_cert':   'Income Certificate',
        'caste_cert':    'Caste Certificate',
        'bank_passbook': 'Bank Passbook',
        'land_record':   'Land Record',
        'disability_cert': 'Disability Certificate',
        'marksheet':     'Marksheet',
        'resume':        'Resume / CV',
        'transcripts':   'Transcripts',
        'domicile':      'Domicile Certificate',
        'pan_card':      'PAN Card',
        'ration_card':   'Ration Card',
        'minority_cert': 'Minority Certificate',
        'admission_letter': 'Admission Letter',
        'experience_cert': 'Experience Certificate',
        'death_cert':    'Death Certificate',
    }
    for field, label in mapping.items():
        if data.get(field):
            docs.append(label)
    return docs


# ==============================
# API ENDPOINT
# ==============================
@csrf_exempt
def match_api(request):
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)

            # Normalise education field from API callers
            # Normalise education field from API callers
            edu_str = payload.get('education_level', '')

            all_schemes = Scheme.objects.all()
            total_fetched = all_schemes.count()
            results = []
            rejected_log = []

            from core.services.matcher import get_best_schemes
            matched_schemes = get_best_schemes(payload, all_schemes)
            
            results = []
            for m in matched_schemes:
                results.append({
                    "name":              m['scheme'],
                    "type":              m['type'],
                    "provider":          m['provider'],
                    "score":             m['score'],
                    "reasons":           m['reasons'],
                    "missing_documents": m['missing_documents'],
                    "status":            m['status'],
                    "deadline":          m['deadline'],
                    "source":            m['source'],
                })

            results_sorted = sorted(results, key=lambda x: x['score'], reverse=True)

            print(
                f"DEBUG-SUMMARY-API | fetched={total_fetched}, "
                f"matched={len(results)}, rejected={total_fetched - len(results)}"
            )

            response_data = {
                "status":          "success",
                "total_fetched":   total_fetched,
                "total_matched":   len(results_sorted),
                "total_rejected":  total_fetched - len(results_sorted),
                "results":         results_sorted,
                "rejected_log":    rejected_log,
            }

            if not results_sorted:
                response_data["message"] = (
                    "No matching opportunities found based on strict eligibility criteria."
                )

            return JsonResponse(response_data)

        except Exception as e:
            logger.exception("match_api error")
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)


def home(request):
    return render(request, 'core/home.html')


# ==============================
# DRF REST API VIEWS
# ==============================
from rest_framework.views import APIView          # noqa: E402
from rest_framework.response import Response      # noqa: E402
from rest_framework import status, generics       # noqa: E402
from rest_framework.pagination import PageNumberPagination  # noqa: E402
from drf_spectacular.utils import extend_schema, OpenApiExample  # noqa: E402

from .models import UserProfile                   # noqa: E402
from .serializers import (                        # noqa: E402
    UserProfileSerializer,
    SchemeSerializer,
    MatchResponseSerializer,
)
from .services.matcher import get_best_schemes    # noqa: E402


class MatchSchemesAPIView(APIView):
    """
    POST /api/match-schemes/

    Accept a user profile, persist it as a UserProfile, run the weighted
    scoring engine against all Scheme objects, and return ranked results.
    """

    @extend_schema(
        summary="Match schemes for a user profile",
        description=(
            "Provide a user profile (name, income, education_level, category, state, marks). "
            "The engine scores every scheme in the database and returns matches sorted by score (max 100)."
        ),
        request=UserProfileSerializer,
        responses={200: MatchResponseSerializer},
        examples=[
            OpenApiExample(
                "Sample Request",
                value={
                    "name": "Bapun",
                    "income": 200000,
                    "education_level": "ug",
                    "category": "obc",
                    "state": "Odisha",
                    "marks": 75,
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = UserProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Persist the profile
        user_profile = serializer.save()

        # Fetch all active schemes
        all_schemes = Scheme.objects.all()
        total_checked = all_schemes.count()

        # Run the matcher (returns list sorted by score desc)
        matches = get_best_schemes(user_profile, all_schemes)

        logger.info(
            "API MATCH | user=%s edu=%s income=%s | matched=%d / %d",
            user_profile.name,
            user_profile.education_level,
            user_profile.income,
            len(matches),
            total_checked,
        )

        response_data = {
            "user":          user_profile.name,
            "total_matched": len(matches),
            "total_checked": total_checked,
            "matches":       matches,
        }

        if not matches:
            response_data["message"] = (
                "No matching opportunities found based on strict eligibility criteria."
            )
        else:
            response_data["message"] = ""

        return Response(response_data, status=status.HTTP_200_OK)


class SchemePagination(PageNumberPagination):
    page_size            = 10
    page_size_query_param = "page_size"
    max_page_size        = 50


class SchemeListAPIView(generics.ListAPIView):
    """
    GET /api/schemes/

    Returns a paginated list of all schemes in the database.
    Supports ?page=N and ?page_size=N query parameters.
    Optional filters: ?type=scholarship  ?provider=govt  ?state=Odisha
    """
    serializer_class = SchemeSerializer
    pagination_class = SchemePagination

    @extend_schema(
        summary="List all schemes (paginated)",
        description="Returns all schemes with pagination (10 per page by default). Filter by type, provider, or state.",
    )
    def get_queryset(self):
        qs = Scheme.objects.all()
        opp_type = self.request.query_params.get("type")
        provider = self.request.query_params.get("provider")
        state    = self.request.query_params.get("state")
        if opp_type:
            qs = qs.filter(opportunity_type__iexact=opp_type)
        if provider:
            qs = qs.filter(provider__iexact=provider)
        if state:
            qs = qs.filter(state__icontains=state)
        return qs