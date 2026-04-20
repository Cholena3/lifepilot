# API Routers module
from fastapi import APIRouter

from app.routers import account, achievement, admin, analytics, auth, badge, budget, course, document, emergency_info, exam, expense, health, health_records, health_share, interview, job_application, life_score, medicine, notification, profile, resume, roadmap, share_link, skill, split, sync, vital, wardrobe, weekly_summary

api_router = APIRouter()

# Include module routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(notification.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(document.router, prefix="/documents", tags=["documents"])
api_router.include_router(share_link.router, prefix="/share-links", tags=["share-links"])
api_router.include_router(expense.router, prefix="/expenses", tags=["money-manager"])
api_router.include_router(budget.router, prefix="/budgets", tags=["money-manager"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["money-manager"])
api_router.include_router(split.router, prefix="/splits", tags=["money-manager"])
api_router.include_router(health_records.router, prefix="/health-records", tags=["health-records"])
api_router.include_router(medicine.router, prefix="/medicines", tags=["medicine-tracker"])
api_router.include_router(vital.router, prefix="/vitals", tags=["vitals-tracker"])
api_router.include_router(emergency_info.router, prefix="/health/emergency", tags=["emergency-info"])
api_router.include_router(health_share.router, prefix="/health/shares", tags=["health-shares"])
api_router.include_router(wardrobe.router, tags=["wardrobe"])
api_router.include_router(skill.router, prefix="/career", tags=["career"])
api_router.include_router(course.router, prefix="/career", tags=["career"])
api_router.include_router(roadmap.router, prefix="/career", tags=["career"])
api_router.include_router(job_application.router, prefix="/career", tags=["career"])
api_router.include_router(interview.router, prefix="/career", tags=["career"])
api_router.include_router(achievement.router, prefix="/career", tags=["career"])
api_router.include_router(resume.router, prefix="/career", tags=["career"])
api_router.include_router(exam.router, tags=["exams"])
api_router.include_router(life_score.router, prefix="/life-score", tags=["analytics"])
api_router.include_router(badge.router, prefix="/badges", tags=["analytics"])
api_router.include_router(weekly_summary.router, prefix="/weekly-summaries", tags=["analytics"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
