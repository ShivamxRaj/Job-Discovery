from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Skill, SkillAlias
from typing import Optional, Dict

class SkillService:
    SKILL_MAP = {
        "reactjs": "React",
        "react js": "React",
        "js": "JavaScript",
        "ts": "TypeScript",
        "nodejs": "Node.js",
        "node js": "Node.js",
        "postgres": "PostgreSQL",
        "ai": "Artificial Intelligence",
        "ml": "Machine Learning",
        "genai": "Generative AI",
        "gen ai": "Generative AI",
    }

    # Hierarchical parent-child relationships
    SKILL_PARENTS = {
        "Machine Learning": "Artificial Intelligence",
        "Generative AI": "Artificial Intelligence",
        "Prompt Engineering": "Generative AI",
        "RAG": "Generative AI",
        "LangGraph": "Generative AI",
        "AI Agents": "Generative AI"
    }

    @classmethod
    def get_canonical_name(cls, raw_skill: str) -> str:
        s = raw_skill.strip().lower()
        canonical = cls.SKILL_MAP.get(s)
        if canonical:
            return canonical
            
        upper_cases = ["rag", "mcp", "ai", "ml", "ctc", "lpa", "wfh", "aws", "gcp", "api", "ui", "ux"]
        words = s.split()
        normalized_words = []
        for w in words:
            if w in upper_cases:
                normalized_words.append(w.upper())
            else:
                normalized_words.append(w.capitalize())
        return " ".join(normalized_words)

    @classmethod
    async def get_or_create_skill(cls, db: AsyncSession, skill_name: str) -> Skill:
        canonical_name = cls.get_canonical_name(skill_name)
        
        # Check if canonical skill exists
        query = select(Skill).where(Skill.name == canonical_name)
        res = await db.execute(query)
        skill = res.scalar_one_or_none()
        
        if not skill:
            # Resolve parent_id if hierarchical mapping exists
            parent_id = None
            parent_name = cls.SKILL_PARENTS.get(canonical_name)
            if parent_name:
                parent_skill = await cls.get_or_create_skill(db, parent_name)
                parent_id = parent_skill.id
                
            skill = Skill(name=canonical_name, parent_id=parent_id)
            db.add(skill)
            await db.commit()
            await db.refresh(skill)
        else:
            parent_name = cls.SKILL_PARENTS.get(canonical_name)
            if parent_name and skill.parent_id is None:
                parent_skill = await cls.get_or_create_skill(db, parent_name)
                skill.parent_id = parent_skill.id
                db.add(skill)
                await db.commit()
                await db.refresh(skill)
            
        # Ensure alias exists mapping raw name to canonical skill
        raw_alias = skill_name.strip()
        if raw_alias.lower() != canonical_name.lower():
            query_alias = select(SkillAlias).where(SkillAlias.alias == raw_alias)
            res_alias = await db.execute(query_alias)
            alias_obj = res_alias.scalar_one_or_none()
            if not alias_obj:
                alias_obj = SkillAlias(alias=raw_alias, skill_id=skill.id)
                db.add(alias_obj)
                await db.commit()
                
        return skill
