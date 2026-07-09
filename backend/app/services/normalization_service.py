import re
from typing import Optional, Tuple, Dict, Any

class NormalizationService:
    # 1. Company Normalization
    COMPANY_SUFFIX_PATTERNS = [
        r'\binc\b\.?', r'\bllc\b\.?', r'\bltd\b\.?', r'\bprivate\s+limited\b\.?', 
        r'\bpvt\s+ltd\b\.?', r'\bgmbh\b\.?', r'\bag\b\.?', r'\bcorp\b\.?', 
        r'\bcorporation\b\.?', r'\bcom\b\.?'
    ]
    
    @classmethod
    def normalize_company(cls, raw_name: str) -> Tuple[str, str]:
        if not raw_name:
            return "Unknown Company", ""
        
        orig = raw_name.strip()
        name = orig.lower()
        
        # Remove common suffixes
        for pat in cls.COMPANY_SUFFIX_PATTERNS:
            name = re.sub(pat, '', name)
        
        # Clean up remaining dots, commas, spaces
        name = re.sub(r'[\s.,\-&]+', ' ', name).strip()
        
        # Capitalize words
        normalized = name.title() if name else orig
        return normalized, orig

    # 2. Title Normalization
    TITLE_MAP = {
        r'\bsr\b\.?': 'Senior',
        r'\bjr\b\.?': 'Junior',
        r'\bdev\b': 'Developer',
        r'\beng\b': 'Engineer',
        r'\bswe\b': 'Software Engineer',
        r'\breactjs\b': 'React',
        r'\breact\s+js\b': 'React',
        r'\bnodejs\b': 'Node.js',
        r'\bnode\s+js\b': 'Node.js',
        r'\bfrontend\s+engineer\b': 'Frontend Developer',
        r'\bfront\s+end\s+engineer\b': 'Frontend Developer',
        r'\bbackend\s+engineer\b': 'Backend Developer',
        r'\bback\s+end\s+engineer\b': 'Backend Developer',
        r'\bfrontend\b': 'Frontend',
        r'\bfront\s+end\b': 'Frontend',
        r'\bbackend\b': 'Backend',
        r'\bback\s+end\b': 'Backend',
        r'\bfullstack\b': 'Full-Stack',
        r'\bfull\s+stack\b': 'Full-Stack',
    }

    @classmethod
    def normalize_title(cls, raw_title: str) -> Tuple[str, str, float]:
        if not raw_title:
            return "Unknown Role", "", 0.5
        
        orig = raw_title.strip()
        title = orig.lower()
        
        matched_any = False
        # Apply specific replacements
        for pat, repl in cls.TITLE_MAP.items():
            if re.search(pat, title, flags=re.IGNORECASE):
                title = re.sub(pat, repl, title, flags=re.IGNORECASE)
                matched_any = True
            
        # Clean extra spaces/punctuation
        title = re.sub(r'[\s\-]+', ' ', title).strip()
        
        # If standard replacement ended up lowering case, fix title casing
        normalized = title.title()
        
        # Special casing adjustments
        normalized = normalized.replace("Node.Js", "Node.js").replace("Full Stack", "Full-Stack")
        
        confidence = 1.0 if matched_any else 0.8
        if "unknown" in normalized.lower():
            confidence = 0.5
            
        return normalized, orig, confidence

    # 3. Employment Type Parser
    @classmethod
    def parse_employment_type(cls, raw_type: Optional[str]) -> str:
        if not raw_type:
            return "UNKNOWN"
        
        t = raw_type.lower().strip()
        if "full" in t:
            return "FULL_TIME"
        if "part" in t:
            return "PART_TIME"
        if "contract" in t or "temp" in t or "temporary" in t:
            return "CONTRACT"
        if "intern" in t:
            return "INTERN"
        if "free" in t or "gig" in t:
            return "FREELANCE"
        
        return "UNKNOWN"

    # 4. Location Normalization
    @classmethod
    def parse_location(cls, loc_str: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str], bool, str, float]:
        # returns (city, state, country, is_remote, remote_type, confidence)
        if not loc_str:
            return None, None, None, False, "Onsite", 0.5
            
        l = loc_str.strip().lower()
        
        # Check Remote status
        is_remote = "remote" in l or "wfh" in l or "home" in l or "anywhere" in l
        remote_type = "Remote" if is_remote else "Onsite"
        if "hybrid" in l:
            remote_type = "Hybrid"
            
        city = None
        state = None
        country = None
        confidence = 0.8
        
        # Delhi NCR Mapping (Delhi, Noida, Gurugram, Gurgaon, NCR)
        if any(x in l for x in ["noida", "gurugram", "gurgaon", "delhi ncr", "delhi-ncr"]):
            city = "Delhi NCR"
            state = "Delhi"
            country = "India"
            confidence = 0.95
        # Standardize Bangalore/India mapping
        elif "bangalore" in l or "bengaluru" in l:
            city = "Bengaluru"
            state = "Karnataka"
            country = "India"
            confidence = 1.0
        elif "india" in l:
            country = "India"
            confidence = 0.9
            
        # Generic state/country parser for standard locations like "San Francisco, CA"
        if not country and "," in loc_str:
            parts = [p.strip() for p in loc_str.split(",")]
            if len(parts) >= 2:
                city = parts[0]
                state = parts[1]
                if len(state) == 2 and state.isupper():
                    country = "United States"
                    confidence = 0.9
                    
        if is_remote and not city:
            confidence = 0.5
            
        return city, state, country, is_remote, remote_type, confidence

    # 5. Salary Parsing
    @classmethod
    def parse_salary(cls, salary_str: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str], str, float]:
        # returns (salary_min, salary_max, currency, salary_period, confidence)
        if not salary_str:
            return None, None, None, "yearly", 0.1
            
        s = salary_str.strip().replace(",", "").lower()
        
        # Competitive/DOE/Negotiable checks
        if any(x in s for x in ["competitive", "negotiable", "doe", "salary commensurate"]):
            return None, None, None, "yearly", 0.1
            
        currency = None
        if "€" in s or "eur" in s:
            currency = "EUR"
        elif "£" in s or "gbp" in s:
            currency = "GBP"
        elif "₹" in s or "inr" in s or "lpa" in s:
            currency = "INR"
        elif "$" in s or "usd" in s:
            currency = "USD"
            
        # Parse period
        period = "yearly"
        if "hour" in s or "/hr" in s or "ph" in s or "hourly" in s:
            period = "hourly"
        elif "month" in s or "/mo" in s or "monthly" in s:
            period = "monthly"
            
        # Extract numbers
        nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', s)]
        if not nums:
            return None, None, currency, period, 0.1
            
        # Handle LPA conversion (e.g. 12 LPA = 1,200,000 INR yearly)
        multiplier = 1.0
        if "k" in s:
            multiplier = 1000.0
        elif "lpa" in s or "lakh" in s or "l" in s:
            multiplier = 100000.0
            
        if len(nums) >= 2:
            s_min = nums[0] * multiplier
            s_max = nums[1] * multiplier
        else:
            s_min = nums[0] * multiplier
            s_max = nums[0] * multiplier
            
        # Determine confidence based on parsing certainty
        if any(x in s for x in ["bonus", "equity", "commission", "ctc", "gross"]):
            confidence = 0.8
        elif any(x in s for x in ["up to", "starting", "max", "min"]):
            confidence = 0.7
        else:
            confidence = 1.0 if currency else 0.5
            
        return s_min, s_max, currency, period, confidence

    # 6. Job Category Classification
    @classmethod
    def classify_category(
        cls,
        title: str,
        skills: Optional[list] = None,
        description: str = "",
        company_name: str = "",
        company_website: str = "",
        job_type: str = ""
    ) -> Tuple[str, float]:
        if not title:
            return "GENERAL_ADMIN", 0.1
            
        t = title.lower()
        desc = description.lower()
        skills_set = {s.lower() for s in skills} if skills else set()
        c_name = company_name.lower()
        c_web = company_website.lower() if company_website else ""
        
        # Define signal maps
        signals = {
            "AI_ML": {
                "title": ["ai", "machine learning", "nlp", "llm", "generative", "rag", "neural", "deep learning", "vision", "prompt", "applied scientist"],
                "skills": ["pytorch", "tensorflow", "keras", "huggingface", "openai", "transformers", "llm", "rag", "nlp", "machine learning", "computer vision"],
                "desc": ["large language models", "generative ai", "neural networks", "deep learning"]
            },
            "CYBERSECURITY": {
                "title": ["security", "cybersecurity", "infosec", "vulnerability", "penetration", "soc", "iam", "compliance"],
                "skills": ["pentest", "vulnerability", "firewall", "cryptography", "iam", "soc", "owasp", "siem"],
                "desc": ["security program", "vulnerabilities", "penetration testing", "cyber security", "threat"]
            },
            "DEVOPS_CLOUD": {
                "title": ["devops", "sre", "platform engineer", "infrastructure", "system admin", "sysadmin", "network", "cloud"],
                "skills": ["kubernetes", "docker", "terraform", "aws", "azure", "gcp", "jenkins", "ansible", "ci/cd", "linux", "system administration"],
                "desc": ["infrastructure", "cloud architecture", "system administrator", "ci/cd pipelines"]
            },
            "DATA_SCIENCE": {
                "title": ["data scientist", "data engineer", "data pipeline", "database administrator", "dba"],
                "skills": ["spark", "hadoop", "etl", "snowflake", "redshift", "data warehouse", "pandas", "numpy", "scala"],
                "desc": ["data engineering", "data pipelines", "big data", "data warehousing"]
            },
            "BUSINESS_ANALYTICS": {
                "title": ["data analyst", "analytics", "bi analyst", "business analyst", "reporting"],
                "skills": ["tableau", "power bi", "excel", "sql", "dashboard", "reporting"],
                "desc": ["business intelligence", "analytical insights", "dashboards", "business analysis"]
            },
            "PRODUCT_MANAGEMENT": {
                "title": ["product manager", "pm", "product owner", "program manager", "scrum master"],
                "skills": ["agile", "scrum", "product roadmap", "jira", "product management"],
                "desc": ["product development", "product strategy", "user stories", "cross-functional teams"]
            },
            "DESIGN_UI_UX": {
                "title": ["designer", "ui", "ux", "graphic", "artist", "cad", "draftsman"],
                "skills": ["figma", "sketch", "photoshop", "illustrator", "ui/ux", "cad", "solidworks", "autocad", "graphic design"],
                "desc": ["design system", "user experience", "user interface", "wireframes", "mockups"]
            },
            "SALES_MARKETING": {
                "title": ["marketing", "sales", "account manager", "growth", "pr", "public relations", "recruitment", "talent acquisition", "hr", "human resources"],
                "skills": ["seo", "sem", "advertising", "social media", "recruitment", "salesforce", "marketing campaigns"],
                "desc": ["sales target", "marketing strategy", "talent acquisition", "public relations"]
            },
            "FINANCE": {
                "title": ["finance", "financial", "accountant", "controller", "billing", "buyer", "purchasing", "procurement"],
                "skills": ["accounting", "ledger", "taxation", "procurement", "auditing", "quickbooks"],
                "desc": ["financial reporting", "budgeting", "purchase orders", "buyer", "invoice"]
            },
            "HEALTHCARE": {
                "title": ["nurse", "dentist", "therapist", "medical", "healthcare", "physician", "doctor", "pathologist"],
                "skills": ["clinical", "nursing", "patient care", "medical terminology", "cpr"],
                "desc": ["patient care", "clinical practice", "hospital environment", "healthcare services"]
            },
            "SOFTWARE_ENGINEERING": {
                "title": ["software", "developer", "programmer", "fullstack", "full-stack", "frontend", "backend", "coder", "architect", "consultant", "engineer"],
                "skills": ["javascript", "typescript", "python", "java", "c#", ".net", "golang", "rust", "c++", "react", "node.js", "django", "fastapi", "html", "css", "git", "rest api"],
                "desc": ["software development", "web application", "backend developer", "frontend developer", "full-stack"]
            }
        }
        
        scores = {}
        for cat, maps in signals.items():
            score = 0.0
            # Title Matches (highest weight) - using word boundary matching
            for kw in maps["title"]:
                if re.search(r'\b' + re.escape(kw) + r'\b', t):
                    score += 5.0
            # Skills Matches
            for kw in maps["skills"]:
                if kw in skills_set or any(re.search(r'\b' + re.escape(kw) + r'\b', s) for s in skills_set):
                    score += 2.0
            # Description Matches
            desc_matches = 0
            for kw in maps["desc"]:
                if re.search(r'\b' + re.escape(kw) + r'\b', desc):
                    desc_matches += 1
            score += min(3.0, desc_matches * 1.0)
            
            # Company name / website matches
            if cat == "HEALTHCARE" and any(re.search(r'\b' + re.escape(x) + r'\b', c_name) or re.search(r'\b' + re.escape(x) + r'\b', c_web) for x in ["hospital", "clinic", "health", "medical", "ascension", "dental"]):
                score += 3.0
            if cat == "FINANCE" and any(re.search(r'\b' + re.escape(x) + r'\b', c_name) or re.search(r'\b' + re.escape(x) + r'\b', c_web) for x in ["bank", "wealth", "finance", "capital", "insurance"]):
                score += 3.0
                
            scores[cat] = score
            
        best_cat = "GENERAL_ADMIN"
        best_score = 0.0
        for cat, score in scores.items():
            if score > best_score:
                best_score = score
                best_cat = cat
                
        if best_score == 0:
            return "GENERAL_ADMIN", 0.1
            
        confidence = min(1.0, max(0.2, best_score / 10.0))
        return best_cat, round(confidence, 2)
