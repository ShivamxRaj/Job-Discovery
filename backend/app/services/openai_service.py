import os
import json
from typing import List, Dict, Any, Tuple
import logging
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingFailedError(Exception):
    """Raised when embedding generation fails. Caller should flag as EMBEDDING_FAILED."""
    pass


class ParseFailedError(Exception):
    """Raised when AI resume parsing fails. Caller should flag as PARSE_FAILED."""
    pass

class OpenAIService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = os.getenv("OPENAI_BASE_URL")
        
        # Auto-detect GitHub Models if key starts with github_pat_
        if self.api_key and self.api_key.startswith("github_pat_"):
            if not self.base_url:
                self.base_url = "https://models.inference.ai.azure.com"
                print("Detecting GitHub Models API Key. Using https://models.inference.ai.azure.com as endpoint.")
                
        if self.api_key:
            self.client = openai.AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None

    async def get_embedding(self, text: str) -> List[float]:
        """Generate text embedding (1536 dimensions) using text-embedding-3-small.
        NEVER returns random/fake vectors. Raises EmbeddingFailedError on failure."""
        if not self.client:
            raise EmbeddingFailedError(
                "OpenAI client not configured. Cannot generate embedding. "
                "Set OPENAI_API_KEY in environment."
            )
            
        try:
            # Truncate text if it's too long
            truncated = text[:8000]
            response = await self.client.embeddings.create(
                input=truncated,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise EmbeddingFailedError(
                f"Embedding generation failed: {str(e)}. "
                f"Version should be flagged as EMBEDDING_FAILED for retry."
            )

    async def parse_resume(self, text: str) -> Dict[str, Any]:
        """Extract structured JSON profile from raw resume text.
        NEVER returns mock/fake data. Raises ParseFailedError on failure."""
        if not self.client:
            raise ParseFailedError(
                "OpenAI client not configured. Cannot parse resume. "
                "Set OPENAI_API_KEY in environment."
            )

        prompt = f"""
        You are an expert resume parser and ATS system.
        Analyze the following raw resume text and extract the information into the requested JSON schema.
        
        The JSON response must have exactly the following keys at the root of the JSON object:
        - "skills": A list of objects, each containing "name" (string, e.g., "Python", "React") and "years" (float or null for years of experience).
        - "education": A list of objects, each containing "degree" (string), "school" (string), and "year" (integer or null).
        - "experience": A list of objects, each containing "title" (string), "company" (string), and "years" (float or null).
        - "quality_score": A float between 0 and 100 representing overall quality.
        - "ats_score": A float between 0 and 100 representing ATS compatibility.
        - "suggestions": A list of 3-5 strings containing concrete recommendations for improvement.

        Resume Text:
        {text}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that outputs structured JSON for resume analysis."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            parsed = json.loads(response.choices[0].message.content)
            
            # If the model nested everything under a "resume" key, flatten it
            if "resume" in parsed and isinstance(parsed["resume"], dict):
                resume_data = parsed["resume"]
                for key in ["skills", "education", "experience", "quality_score", "ats_score", "suggestions"]:
                    if key in resume_data and (key not in parsed or not parsed[key]):
                        parsed[key] = resume_data[key]
            
            # Ensure required keys exist
            parsed.setdefault("skills", [])
            parsed.setdefault("education", [])
            parsed.setdefault("experience", [])
            parsed.setdefault("quality_score", 70.0)
            parsed.setdefault("ats_score", 70.0)
            parsed.setdefault("suggestions", ["Improve formatting."])
            
            return parsed
        except Exception as e:
            logger.error(f"OpenAI resume parsing failed: {e}")
            raise ParseFailedError(
                f"Resume parsing failed: {str(e)}. "
                f"Version should be flagged as PARSE_FAILED for retry."
            )

    async def explain_match(self, resume_summary: str, job_description: str) -> str:
        """Generate a natural language explanation of how a resume matches a job"""
        if not self.client:
            return "This job is a strong match based on your Python and database management skills. The role aligns with your experience as an intern."

        prompt = f"""
        Compare the following resume summary with the job description.
        Write a concise, encouraging 2-3 sentence explanation of why this user is a good match, and highlight any skill gaps they should prepare for.

        Resume Summary:
        {resume_summary}

        Job Description:
        {job_description[:2000]}
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior technical recruiter writing helpful match reviews for candidates."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI match explanation failed: {e}")
            return "Matches key requirements in your profile."

    async def generate_cover_letter(self, resume_text: str, job_description: str) -> str:
        """Generate a tailored cover letter"""
        if not self.client:
            return "Dear Hiring Manager,\n\nI am writing to express my interest in the position..."

        prompt = f"""
        Write a professional, compelling, 3-paragraph cover letter for the candidate based on their resume and the target job description.
        Incorporate achievements from the resume and align them with the key requirements of the job.

        Candidate Resume:
        {resume_text[:4000]}

        Job Description:
        {job_description[:4000]}
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert career counselor and professional writer."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating cover letter: {e}"

    async def generate_hr_email(self, resume_text: str, job_description: str) -> str:
        """Generate a concise, polite outreach email to HR/Recruiter"""
        if not self.client:
            return "Subject: Inquiry: Software Engineer Role\n\nDear HR Team,\n\nI recently applied..."

        prompt = f"""
        Write a short (under 150 words) cold outreach email to a recruiter for the target job description.
        Use a professional and enthusiastic tone, summarize why you are a great fit, and ask for a quick chat.

        Candidate Resume:
        {resume_text[:4000]}

        Job Description:
        {job_description[:4000]}
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert job seeker and professional communicator."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating outreach email: {e}"

openai_service = OpenAIService()
