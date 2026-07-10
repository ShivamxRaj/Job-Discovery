import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.models import JobRecommendation, Job, User
from app.repositories.application import application_repo

async def run_verification():
    async with async_session_maker() as db:
        # Get latest 100 recommendations
        query = select(JobRecommendation).order_by(JobRecommendation.created_at.desc()).limit(100)
        from sqlalchemy.orm import selectinload
        query = query.options(selectinload(JobRecommendation.job).selectinload(Job.company))
        result = await db.execute(query)
        recs = result.scalars().all()

        if not recs:
            print("No recommendations found to verify.")
            return

        print(f"=== Recommendation Verification Report ===")
        print(f"Total Recommendations Analyzed: {len(recs)}\n")

        print("--- Sample (Top 5) ---")
        for rec in recs[:5]:
            import json
            exp_data = None
            is_explainable = False
            evidence_confidence = "Low"
            
            try:
                exp_data = json.loads(rec.explanation)
                is_explainable = exp_data.get("is_explainable", False)
                evidence_confidence = exp_data.get("evidence_confidence", "Unknown")
            except:
                pass
                
            print(f"Title: {rec.job.title}")
            print(f"Company: {rec.job.company.name if rec.job.company else 'N/A'}")
            print(f"Category: {rec.job.job_category}")
            print(f"Origin: {rec.job.data_origin}")
            print(f"Embedding: {rec.job.embedding_status}")
            print(f"Salary Conf: {rec.job.salary_confidence} | Category Conf: {rec.job.category_confidence}")
            print(f"Overall Score: {rec.score}")
            print(f"Explainable: {is_explainable} (Confidence: {evidence_confidence})")
            print("-" * 30)

        # Metrics
        explainable_count = 0
        categories = set()
        sources = set()
        total_confidence = 0.0

        for rec in recs:
            categories.add(rec.job.job_category)
            sources.add(rec.job.data_origin)
            total_confidence += (rec.job.category_confidence or 0.5)
            
            try:
                import json
                exp_data = json.loads(rec.explanation)
                if exp_data.get("is_explainable", False):
                    explainable_count += 1
            except:
                pass

        # Simulated Precision@10 / Diversity@10 (Assuming top 10 from one user run)
        # We'll just proxy the logic based on the 100 samples
        precision_at_10 = "N/A (Requires ground truth labels)"
        diversity_at_10 = min(1.0, len(categories) / min(len(recs), 10.0))

        print("\n=== System Metrics ===")
        print(f"Explainability Coverage: {explainable_count}/{len(recs)} ({(explainable_count/len(recs))*100:.1f}%)")
        print(f"Precision@10 (proxy score threshold > 70): {sum(1 for r in recs[:10] if r.score > 70) / min(len(recs), 10) * 100:.1f}%")
        print(f"Diversity@10: {diversity_at_10:.2f}")
        print(f"Category Diversity: {len(categories)} unique categories")
        print(f"Source Diversity: {len(sources)} unique sources")
        print(f"Average Confidence: {total_confidence / len(recs):.2f}")
        
        print("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())
