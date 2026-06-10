import asyncio
from datetime import datetime
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..models.job import Benefit, ExperienceLevel, Job, JobType, Location, Salary

logger = logging.getLogger(__name__)


class NYCJobsAPIClient:
    """Async client for the NYC Jobs (Socrata) dataset."""

    BASE_URL = "https://data.cityofnewyork.us/resource/kpav-sd4t.json"

    def __init__(self, app_token: Optional[str] = None, timeout: float = 30.0):
        self.timeout = timeout
        self.headers = {"Accept": "application/json"}
        if app_token:
            self.headers["X-App-Token"] = app_token

    async def fetch_jobs(
        self,
        limit: int = 1000,
        order: str = "posting_date DESC",
        chunk_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Fetch NYC job postings with pagination."""
        results: List[Dict[str, Any]] = []
        offset = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while len(results) < limit:
                current_limit = min(chunk_size, limit - len(results))
                params = {
                    "$limit": current_limit,
                    "$offset": offset,
                    "$order": order,
                }

                response = await client.get(
                    self.BASE_URL, params=params, headers=self.headers
                )
                response.raise_for_status()
                page = response.json()

                if not page:
                    break

                results.extend(page)
                offset += current_limit

                # Socrata rate limits burst requests; be polite
                await asyncio.sleep(0.2)

        return results


class NYCJobsAdapter:
    """Convert NYC Jobs (Socrata) records into internal Job models."""

    BOROUGH_MAP = {
        "manhattan": ("New York", "NY"),
        "bronx": ("Bronx", "NY"),
        "brooklyn": ("Brooklyn", "NY"),
        "queens": ("Queens", "NY"),
        "staten island": ("Staten Island", "NY"),
    }

    DEFAULT_SKILL_CLUES: Dict[str, List[str]] = {
        "react": ["react", "react.js", "reactjs"],
        "javascript": ["javascript", "js", "ecmascript"],
        "python": ["python"],
        "sql": ["sql", "structured query language"],
        "data-engineering": ["data engineering", "etl", "data pipeline", "data integration"],
        "project-management": ["project management", "pmp", "agile", "scrum", "ms project"],
        "procurement": ["procurement", "purchasing", "sourcing", "supply management"],
        "contract-management": ["contract management", "contract administration", "negotiation"],
        "operations-analytics": ["data analysis", "analytics", "insights", "reporting"],
        "power-bi": ["power bi", "power-bi"],
        "tableau": ["tableau"],
        "excel": ["excel", "microsoft excel", "spreadsheets"],
        "aws": ["aws", "amazon web services"],
        "gis": ["gis", "geographic information system"],
        "arcgis": ["arcgis", "arcmap", "arc-pro", "arc pro"],
        "autocad": ["autocad", "civil 3d", "cad"],
        "public-health": ["public health", "epidemiology", "health promotion"],
        "osha": ["osha", "occupational safety", "safety compliance"],
        "social-work": ["social work", "case manager", "lcsw"],
        "customer-service": ["customer service", "constituent services", "call center"],
        "bilingual-spanish": ["bilingual spanish", "spanish speaking", "spanish fluency"],
    }

    def __init__(
        self,
        app_token: Optional[str] = None,
        skill_clues: Optional[Dict[str, List[str]]] = None,
    ):
        self.client = NYCJobsAPIClient(app_token=app_token)
        self.skill_clues = skill_clues or self.DEFAULT_SKILL_CLUES

    async def fetch_and_map_jobs(
        self,
        limit: int = 1500,
        order: str = "posting_date DESC",
    ) -> List[Tuple[Job, Dict[str, Any]]]:
        """Fetch NYC jobs and map them into Job models."""
        raw_records = await self.client.fetch_jobs(limit=limit, order=order)
        mapped: List[Tuple[Job, Dict[str, Any]]] = []

        for record in raw_records:
            try:
                job = self.map_record(record)
                mapped.append((job, record))
            except Exception as exc:
                job_id = record.get("job_id")
                logger.warning(f"Failed to map NYC job {job_id}: {exc}")

        return mapped

    def map_record(self, record: Dict[str, Any]) -> Job:
        job_id = record.get("job_id") or self._build_fallback_id(record)
        job_identifier = f"nyc_{job_id}"

        title = (
            record.get("business_title")
            or record.get("civil_service_title")
            or "NYC Job Opening"
        )

        description = self._compose_description(record)
        company_name = record.get("agency", "City of New York")
        location = self._parse_location(
            record.get("work_location"), record.get("work_location_1")
        )
        job_type = self._map_job_type(record.get("full_time_part_time_indicator"))
        experience = self._map_experience_level(record.get("career_level"))
        salary = self._parse_salary(record)
        required_skills = self._extract_declared_skills(record)
        preferred_skills = self._split_text_field(record.get("preferred_skills"))
        responsibilities = self._split_text_field(record.get("job_description"))
        requirements = self._split_text_field(record.get("minimum_qual_requirements"))
        posted_date = self._parse_datetime(
            record.get("posting_date") or record.get("posting_updated")
        )
        application_deadline = self._parse_datetime(record.get("post_until"))

        remote_allowed = self._contains_keyword(description, ["remote", "hybrid"])
        visa_sponsorship = self._contains_keyword(description, ["visa sponsorship"])

        source_url = f"https://cityjobs.nyc.gov/jobsearch.html?job_id={job_id}"
        to_apply = (record.get("to_apply") or "").strip()
        apply_url = to_apply if self._looks_like_url(to_apply) else source_url

        benefits: List[Benefit] = []
        if record.get("residency_requirement"):
            benefits.append(
                Benefit(
                    name="Residency Requirement",
                    description=record.get("residency_requirement"),
                    category="eligibility",
                )
            )

        job = Job(
            id=job_identifier,
            title=title.strip(),
            description=description,
            company_name=company_name.strip(),
            location=location,
            job_type=job_type,
            experience_level=experience,
            salary=salary,
            benefits=benefits,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            responsibilities=responsibilities,
            requirements=requirements,
            posted_date=posted_date,
            application_deadline=application_deadline,
            remote_allowed=remote_allowed,
            visa_sponsorship=visa_sponsorship,
            source_url=source_url,
            apply_url=apply_url,
        )

        return job

    def _build_fallback_id(self, record: Dict[str, Any]) -> str:
        title = (record.get("business_title") or "nyc_job").lower().replace(" ", "_")
        process_date = record.get("process_date", datetime.utcnow().isoformat())
        return f"{title}_{process_date}"

    def _compose_description(self, record: Dict[str, Any]) -> str:
        sections = [
            record.get("job_description"),
            self._render_section("Minimum Qualifications", record.get("minimum_qual_requirements")),
            self._render_section("Preferred Skills", record.get("preferred_skills")),
            self._render_section("Additional Information", record.get("additional_information")),
            self._render_section("To Apply", record.get("to_apply")),
        ]
        return "\n\n".join(section for section in sections if section)

    def _render_section(self, title: str, content: Optional[str]) -> Optional[str]:
        if not content:
            return None
        cleaned = content.strip()
        if not cleaned:
            return None
        return f"{title}:\n{cleaned}"

    def _parse_location(
        self, primary: Optional[str], secondary: Optional[str]
    ) -> Location:
        text = (secondary or primary or "New York, NY").lower()
        for keyword, (city, state) in self.BOROUGH_MAP.items():
            if keyword in text:
                return Location(city=city, state=state, country="USA")

        if "ny" in text:
            return Location(city="New York", state="NY", country="USA")
        if "brooklyn" in text:
            return Location(city="Brooklyn", state="NY", country="USA")

        return Location(city="New York", state="NY", country="USA")

    def _map_job_type(self, indicator: Optional[str]) -> JobType:
        indicator = (indicator or "").strip().lower()
        mapping = {
            "f": JobType.FULL_TIME,
            "full-time": JobType.FULL_TIME,
            "full time": JobType.FULL_TIME,
            "p": JobType.PART_TIME,
            "part-time": JobType.PART_TIME,
            "part time": JobType.PART_TIME,
            "t": JobType.CONTRACT,
            "c": JobType.CONTRACT,
            "intern": JobType.INTERNSHIP,
        }
        return mapping.get(indicator, JobType.FULL_TIME)

    def _map_experience_level(self, level: Optional[str]) -> ExperienceLevel:
        if not level:
            return ExperienceLevel.MID

        level_lower = level.lower()
        if "entry" in level_lower or "intern" in level_lower:
            return ExperienceLevel.ENTRY
        if "executive" in level_lower or "director" in level_lower:
            return ExperienceLevel.EXECUTIVE
        if "senior" in level_lower or "manager" in level_lower:
            return ExperienceLevel.SENIOR
        return ExperienceLevel.MID

    def _parse_salary(self, record: Dict[str, Any]) -> Optional[Salary]:
        try:
            min_salary = int(record.get("salary_range_from")) if record.get("salary_range_from") else None
            max_salary = int(record.get("salary_range_to")) if record.get("salary_range_to") else None
        except ValueError:
            min_salary = max_salary = None

        period = (record.get("salary_frequency") or "annual").lower()
        period_mapping = {
            "annual": "yearly",
            "year": "yearly",
            "hourly": "hourly",
            "daily": "daily",
        }

        if min_salary or max_salary:
            return Salary(
                min_salary=min_salary,
                max_salary=max_salary,
                currency="USD",
                period=period_mapping.get(period, "yearly"),
            )
        return None

    def _split_text_field(self, text: Optional[str]) -> List[str]:
        if not text:
            return []
        separators = re.split(r"[\n;\r•]+", text)
        return [segment.strip() for segment in separators if segment.strip()]

    def _extract_declared_skills(self, record: Dict[str, Any]) -> List[str]:
        text_fields = [
            record.get("job_description"),
            record.get("preferred_skills"),
            record.get("minimum_qual_requirements"),
            record.get("additional_information"),
        ]
        combined = " ".join(field.lower() for field in text_fields if field)
        found = set()

        for canonical, clues in self.skill_clues.items():
            for clue in clues:
                if clue.lower() in combined:
                    found.add(canonical)
                    break

        return sorted(found)

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", ""))
        except ValueError:
            return None

    def _contains_keyword(self, text: str, keywords: List[str]) -> bool:
        lowered = text.lower()
        return any(keyword in lowered for keyword in keywords)

    def _looks_like_url(self, text: str) -> bool:
        return bool(re.match(r"https?://", text or ""))
