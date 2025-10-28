import os
import logging
from typing import List, Optional
from django.db import transaction
from .models import ScrutinyResult
from .nlp_utils import analyze_file
from exams.models import Request

logger = logging.getLogger(__name__)

def get_existing_questions_for_subject(subject_code: str) -> List[str]:
    """
    Retrieve existing questions from previous papers for the same subject.
    Used for plagiarism detection.
    """
    try:
        # Get all final papers for the same subject
        from exams.models import FinalPapers
        previous_papers = FinalPapers.objects.filter(
            s_code=subject_code
        ).exclude(paper__isnull=True).exclude(paper='')
        
        existing_questions = []
        for paper in previous_papers:
            if paper.paper and os.path.exists(paper.paper.path):
                try:
                    analysis = analyze_file(paper.paper.path)
                    questions = analysis.get('summary', {}).get('sample_questions', [])
                    existing_questions.extend(questions)
                except Exception as e:
                    logger.warning(f"Failed to extract questions from {paper.paper.path}: {e}")
                    continue
        
        return existing_questions
    except Exception as e:
        logger.error(f"Error retrieving existing questions: {e}")
        return []

def perform_automatic_scrutiny(request_obj: Request, temp_file_path: str) -> Optional[ScrutinyResult]:
    """
    Perform automatic scrutiny analysis on an uploaded paper.
    This function is called when a teacher uploads a paper.
    """
    try:
        if not temp_file_path or not os.path.exists(temp_file_path):
            logger.warning(f"No temp file found for request {request_obj.id}")
            return None
        
        logger.info(f"Starting automatic scrutiny for request {request_obj.id}")
        
        # Get existing questions for plagiarism detection
        existing_questions = get_existing_questions_for_subject(request_obj.s_code)
        
        # Perform comprehensive analysis
        analysis_result = analyze_file(temp_file_path, existing_questions)
        
        # Create scrutiny result
        with transaction.atomic():
            scrutiny_result = ScrutinyResult.objects.create(
                request_obj=request_obj,
                summary=analysis_result.get('summary', {})
            )
        
        logger.info(f"Automatic scrutiny completed for request {request_obj.id}")
        return scrutiny_result
        
    except Exception as e:
        logger.exception(f"Error in automatic scrutiny for request {request_obj.id}: {e}")
        # Create a basic scrutiny result with error information
        try:
            with transaction.atomic():
                scrutiny_result = ScrutinyResult.objects.create(
                    request_obj=request_obj,
                    summary={
                        "error": str(e),
                        "num_questions": 0,
                        "overall_score": 0.0,
                        "recommendations": ["Analysis failed due to technical error"]
                    }
                )
            return scrutiny_result
        except Exception as create_error:
            logger.exception(f"Failed to create error scrutiny result: {create_error}")
            return None

def get_scrutiny_summary_for_dashboard() -> dict:
    """
    Get summary statistics for the COE dashboard.
    """
    try:
        total_papers = ScrutinyResult.objects.count()
        
        if total_papers == 0:
            return {
                "total_papers": 0,
                "average_score": 0.0,
                "papers_needing_review": 0,
                "plagiarism_issues": 0,
                "quality_distribution": {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
            }
        
        # Calculate statistics
        results = ScrutinyResult.objects.all()
        
        scores = []
        papers_needing_review = 0
        plagiarism_issues = 0
        quality_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        
        for result in results:
            summary = result.summary
            score = summary.get('overall_score', 0.0)
            scores.append(score)
            
            # Count papers needing review (low score or plagiarism issues)
            if score < 0.6:
                papers_needing_review += 1
            
            # Count plagiarism issues
            plagiarism_score = summary.get('plagiarism_analysis', {}).get('plagiarism_score', 0.0)
            if plagiarism_score > 0.3:
                plagiarism_issues += 1
            
            # Quality distribution
            if score >= 0.8:
                quality_distribution["excellent"] += 1
            elif score >= 0.6:
                quality_distribution["good"] += 1
            elif score >= 0.4:
                quality_distribution["fair"] += 1
            else:
                quality_distribution["poor"] += 1
        
        average_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            "total_papers": total_papers,
            "average_score": round(average_score, 2),
            "papers_needing_review": papers_needing_review,
            "plagiarism_issues": plagiarism_issues,
            "quality_distribution": quality_distribution
        }
        
    except Exception as e:
        logger.exception(f"Error getting scrutiny summary: {e}")
        return {
            "total_papers": 0,
            "average_score": 0.0,
            "papers_needing_review": 0,
            "plagiarism_issues": 0,
            "quality_distribution": {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        }
