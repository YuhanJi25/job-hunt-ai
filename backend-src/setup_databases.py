#!/usr/bin/env python3
"""
Setup script for initializing databases and creating sample data
"""

import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_elasticsearch, get_neo4j
from app.models.job import Job, JobType, ExperienceLevel, Location, Salary, Benefit
from app.services.elasticsearch_service import ElasticsearchService
from app.services.knowledge_graph_service import KnowledgeGraphService

def create_sample_jobs() -> List[Job]:
    """Create sample job data"""
    jobs = []
    
    # Sample job 1: Software Developer at Google
    job1 = Job(
        id="job_001",
        title="Senior Software Engineer - AI/ML",
        description="""
        We are looking for a Senior Software Engineer to join our AI/ML team at Google. 
        You will be working on cutting-edge machine learning projects, developing algorithms 
        for natural language processing, and building scalable AI systems. This role involves 
        solving complex technical challenges, conducting research on AI topics, and integrating 
        AI solutions for industry-level applications.
        
        You will work closely with research scientists and product teams to translate 
        research into production systems. The ideal candidate has experience with 
        machine learning frameworks, distributed systems, and has a passion for AI research.
        """,
        company_name="Google",
        location=Location(
            city="Mountain View",
            state="California",
            country="USA",
            coordinates={"lat": 37.422, "lng": -122.084}
        ),
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.SENIOR,
        salary=Salary(
            min_salary=200000,
            max_salary=300000,
            currency="USD",
            period="yearly"
        ),
        benefits=[
            Benefit(name="Health Insurance", category="health"),
            Benefit(name="401k Matching", category="retirement"),
            Benefit(name="H1B Sponsorship", category="visa"),
            Benefit(name="Stock Options", category="equity")
        ],
        required_skills=[
            "Python", "Machine Learning", "TensorFlow", "PyTorch", 
            "Distributed Systems", "Kubernetes", "Docker", "SQL"
        ],
        preferred_skills=[
            "Natural Language Processing", "Computer Vision", "Research", 
            "Publications", "PhD", "Go", "Java"
        ],
        responsibilities=[
            "Develop and deploy machine learning models at scale",
            "Research and implement new AI algorithms",
            "Collaborate with research teams on cutting-edge projects",
            "Build and maintain distributed ML systems",
            "Mentor junior engineers and contribute to technical strategy"
        ],
        requirements=[
            "5+ years of software engineering experience",
            "Strong background in machine learning and AI",
            "Experience with ML frameworks (TensorFlow, PyTorch)",
            "Proficiency in Python and distributed systems",
            "PhD or equivalent research experience preferred"
        ],
        posted_date=datetime.now() - timedelta(days=2),
        remote_allowed=True,
        visa_sponsorship=True
    )
    jobs.append(job1)
    
    # Sample job 2: AI Research Scientist at OpenAI
    job2 = Job(
        id="job_002",
        title="AI Research Scientist",
        description="""
        Join OpenAI's research team to push the boundaries of artificial intelligence. 
        You will conduct groundbreaking research in areas such as large language models, 
        reinforcement learning, and AI safety. This role involves publishing research papers, 
        developing novel algorithms, and working on projects that could shape the future of AI.
        
        You'll work in a collaborative environment with world-class researchers and have 
        access to cutting-edge computing resources. The ideal candidate has a strong 
        research background and a passion for advancing AI capabilities.
        """,
        company_name="OpenAI",
        location=Location(
            city="San Francisco",
            state="California",
            country="USA",
            coordinates={"lat": 37.7749, "lng": -122.4194}
        ),
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.SENIOR,
        salary=Salary(
            min_salary=250000,
            max_salary=400000,
            currency="USD",
            period="yearly"
        ),
        benefits=[
            Benefit(name="Health Insurance", category="health"),
            Benefit(name="401k Matching", category="retirement"),
            Benefit(name="H1B Sponsorship", category="visa"),
            Benefit(name="Research Budget", category="professional")
        ],
        required_skills=[
            "Python", "Machine Learning", "Deep Learning", "Research", 
            "PyTorch", "TensorFlow", "Statistics", "Linear Algebra"
        ],
        preferred_skills=[
            "Natural Language Processing", "Large Language Models", 
            "Reinforcement Learning", "AI Safety", "Publications", "PhD"
        ],
        responsibilities=[
            "Conduct original research in AI and machine learning",
            "Publish research papers in top-tier conferences",
            "Develop and implement novel AI algorithms",
            "Collaborate with interdisciplinary research teams",
            "Contribute to OpenAI's research strategy and direction"
        ],
        requirements=[
            "PhD in Computer Science, AI, or related field",
            "Strong publication record in AI/ML conferences",
            "Expertise in deep learning and neural networks",
            "Proficiency in Python and ML frameworks",
            "Experience with large-scale model training"
        ],
        posted_date=datetime.now() - timedelta(days=1),
        remote_allowed=False,
        visa_sponsorship=True
    )
    jobs.append(job2)
    
    # Sample job 3: Software Engineer at Microsoft
    job3 = Job(
        id="job_003",
        title="Software Engineer - Azure AI",
        description="""
        Microsoft Azure AI team is seeking a Software Engineer to build and scale AI services. 
        You will work on Azure Cognitive Services, developing APIs and services that enable 
        developers to integrate AI capabilities into their applications. This role involves 
        working with machine learning models, building scalable cloud services, and solving 
        complex engineering challenges.
        
        You'll collaborate with product managers, data scientists, and other engineers to 
        deliver high-quality AI services to millions of users worldwide.
        """,
        company_name="Microsoft",
        location=Location(
            city="Seattle",
            state="Washington",
            country="USA",
            coordinates={"lat": 47.6062, "lng": -122.3321}
        ),
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.MID,
        salary=Salary(
            min_salary=150000,
            max_salary=220000,
            currency="USD",
            period="yearly"
        ),
        benefits=[
            Benefit(name="Health Insurance", category="health"),
            Benefit(name="401k Matching", category="retirement"),
            Benefit(name="H1B Sponsorship", category="visa"),
            Benefit(name="Stock Options", category="equity")
        ],
        required_skills=[
            "C#", "Python", "Azure", "Machine Learning", "REST APIs", 
            "Microservices", "Docker", "Kubernetes"
        ],
        preferred_skills=[
            "Cognitive Services", "Computer Vision", "NLP", 
            "Distributed Systems", "Go", "JavaScript"
        ],
        responsibilities=[
            "Develop and maintain Azure AI services",
            "Build scalable APIs for AI capabilities",
            "Work with machine learning models in production",
            "Collaborate with cross-functional teams",
            "Ensure high availability and performance of services"
        ],
        requirements=[
            "3+ years of software engineering experience",
            "Experience with cloud platforms (Azure preferred)",
            "Strong programming skills in C# or Python",
            "Understanding of machine learning concepts",
            "Experience with distributed systems"
        ],
        posted_date=datetime.now() - timedelta(days=3),
        remote_allowed=True,
        visa_sponsorship=True
    )
    jobs.append(job3)
    
    # Sample job 4: Data Scientist at Netflix
    job4 = Job(
        id="job_004",
        title="Senior Data Scientist - Recommendation Systems",
        description="""
        Netflix is looking for a Senior Data Scientist to work on our recommendation systems. 
        You will develop algorithms that help millions of users discover content they love. 
        This role involves working with large-scale data, building machine learning models, 
        and conducting A/B tests to improve user experience.
        
        You'll work with petabytes of data and have the opportunity to impact how people 
        discover and enjoy entertainment worldwide.
        """,
        company_name="Netflix",
        location=Location(
            city="Los Gatos",
            state="California",
            country="USA",
            coordinates={"lat": 37.2264, "lng": -121.9736}
        ),
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.SENIOR,
        salary=Salary(
            min_salary=180000,
            max_salary=280000,
            currency="USD",
            period="yearly"
        ),
        benefits=[
            Benefit(name="Health Insurance", category="health"),
            Benefit(name="401k Matching", category="retirement"),
            Benefit(name="H1B Sponsorship", category="visa"),
            Benefit(name="Unlimited PTO", category="time_off")
        ],
        required_skills=[
            "Python", "Machine Learning", "Statistics", "SQL", 
            "Spark", "A/B Testing", "Recommendation Systems", "Pandas"
        ],
        preferred_skills=[
            "Deep Learning", "TensorFlow", "PyTorch", "Big Data", 
            "Scala", "R", "PhD", "Research Experience"
        ],
        responsibilities=[
            "Develop and improve recommendation algorithms",
            "Design and analyze A/B tests",
            "Work with large-scale datasets using Spark",
            "Collaborate with engineering and product teams",
            "Present findings to stakeholders and leadership"
        ],
        requirements=[
            "5+ years of data science experience",
            "Strong background in machine learning and statistics",
            "Experience with recommendation systems",
            "Proficiency in Python and SQL",
            "Experience with large-scale data processing"
        ],
        posted_date=datetime.now() - timedelta(days=5),
        remote_allowed=True,
        visa_sponsorship=True
    )
    jobs.append(job4)
    
    # Sample job 5: Full Stack Developer at Stripe
    job5 = Job(
        id="job_005",
        title="Full Stack Engineer - Payments Platform",
        description="""
        Stripe is seeking a Full Stack Engineer to join our payments platform team. 
        You will build and maintain the core infrastructure that processes billions of 
        dollars in payments. This role involves working with both frontend and backend 
        systems, solving complex technical challenges, and ensuring high reliability 
        and performance.
        
        You'll work in a fast-paced environment with talented engineers and have the 
        opportunity to impact how businesses around the world handle payments.
        """,
        company_name="Stripe",
        location=Location(
            city="San Francisco",
            state="California",
            country="USA",
            coordinates={"lat": 37.7749, "lng": -122.4194}
        ),
        job_type=JobType.FULL_TIME,
        experience_level=ExperienceLevel.MID,
        salary=Salary(
            min_salary=160000,
            max_salary=240000,
            currency="USD",
            period="yearly"
        ),
        benefits=[
            Benefit(name="Health Insurance", category="health"),
            Benefit(name="401k Matching", category="retirement"),
            Benefit(name="H1B Sponsorship", category="visa"),
            Benefit(name="Stock Options", category="equity")
        ],
        required_skills=[
            "JavaScript", "React", "Node.js", "Python", "PostgreSQL", 
            "Redis", "Docker", "AWS"
        ],
        preferred_skills=[
            "TypeScript", "GraphQL", "Microservices", "Kubernetes", 
            "Go", "Ruby", "Fintech Experience"
        ],
        responsibilities=[
            "Build and maintain payment processing systems",
            "Develop both frontend and backend components",
            "Ensure high availability and performance",
            "Collaborate with product and design teams",
            "Participate in code reviews and technical discussions"
        ],
        requirements=[
            "3+ years of full-stack development experience",
            "Strong proficiency in JavaScript and Python",
            "Experience with React and Node.js",
            "Understanding of database systems",
            "Experience with cloud platforms"
        ],
        posted_date=datetime.now() - timedelta(days=4),
        remote_allowed=True,
        visa_sponsorship=True
    )
    jobs.append(job5)
    
    return jobs

def create_skill_relationships() -> List[Dict[str, Any]]:
    """Create skill relationships for the knowledge graph"""
    relationships = [
        # Programming Languages
        {"skill1": "Python", "skill2": "Machine Learning", "type": "used_with", "confidence": 0.9},
        {"skill1": "Python", "skill2": "Data Science", "type": "used_with", "confidence": 0.9},
        {"skill1": "Python", "skill2": "Web Development", "type": "used_with", "confidence": 0.8},
        {"skill1": "JavaScript", "skill2": "React", "type": "used_with", "confidence": 0.9},
        {"skill1": "JavaScript", "skill2": "Node.js", "type": "used_with", "confidence": 0.9},
        {"skill1": "C#", "skill2": ".NET", "type": "used_with", "confidence": 0.9},
        
        # ML/AI Skills
        {"skill1": "Machine Learning", "skill2": "Deep Learning", "type": "is_a", "confidence": 0.8},
        {"skill1": "Deep Learning", "skill2": "Neural Networks", "type": "is_a", "confidence": 0.9},
        {"skill1": "Machine Learning", "skill2": "Natural Language Processing", "type": "related_to", "confidence": 0.8},
        {"skill1": "Machine Learning", "skill2": "Computer Vision", "type": "related_to", "confidence": 0.8},
        {"skill1": "TensorFlow", "skill2": "Deep Learning", "type": "used_with", "confidence": 0.9},
        {"skill1": "PyTorch", "skill2": "Deep Learning", "type": "used_with", "confidence": 0.9},
        
        # Cloud and Infrastructure
        {"skill1": "AWS", "skill2": "Cloud Computing", "type": "is_a", "confidence": 0.9},
        {"skill1": "Azure", "skill2": "Cloud Computing", "type": "is_a", "confidence": 0.9},
        {"skill1": "Docker", "skill2": "Containerization", "type": "is_a", "confidence": 0.9},
        {"skill1": "Kubernetes", "skill2": "Container Orchestration", "type": "is_a", "confidence": 0.9},
        {"skill1": "Docker", "skill2": "Kubernetes", "type": "used_with", "confidence": 0.8},
        
        # Databases
        {"skill1": "SQL", "skill2": "Database Management", "type": "is_a", "confidence": 0.9},
        {"skill1": "PostgreSQL", "skill2": "SQL", "type": "is_a", "confidence": 0.9},
        {"skill1": "MongoDB", "skill2": "NoSQL", "type": "is_a", "confidence": 0.9},
        {"skill1": "Redis", "skill2": "In-Memory Database", "type": "is_a", "confidence": 0.9},
        
        # Web Development
        {"skill1": "React", "skill2": "Frontend Development", "type": "is_a", "confidence": 0.9},
        {"skill1": "Node.js", "skill2": "Backend Development", "type": "is_a", "confidence": 0.9},
        {"skill1": "REST APIs", "skill2": "API Development", "type": "is_a", "confidence": 0.9},
        {"skill1": "GraphQL", "skill2": "API Development", "type": "is_a", "confidence": 0.9},
        
        # Data Science
        {"skill1": "Pandas", "skill2": "Data Analysis", "type": "used_with", "confidence": 0.9},
        {"skill1": "NumPy", "skill2": "Data Analysis", "type": "used_with", "confidence": 0.9},
        {"skill1": "Statistics", "skill2": "Data Science", "type": "prerequisite_for", "confidence": 0.9},
        {"skill1": "A/B Testing", "skill2": "Data Science", "type": "used_with", "confidence": 0.8},
    ]
    
    return relationships

def setup_databases():
    """Setup databases with sample data"""
    print("🚀 Setting up Job Matching Application databases...")
    
    # Initialize services
    es_service = ElasticsearchService()
    kg_service = KnowledgeGraphService()
    
    print("✅ Services initialized")
    
    # Create sample jobs
    print("📝 Creating sample jobs...")
    sample_jobs = create_sample_jobs()
    
    # Index jobs in Elasticsearch
    print("🔍 Indexing jobs in Elasticsearch...")
    bulk_result = es_service.bulk_index_jobs(sample_jobs)
    print(f"✅ Indexed {len(sample_jobs)} jobs in Elasticsearch")
    
    # Create job nodes in Neo4j
    print("🕸️ Creating job nodes in Neo4j...")
    for job in sample_jobs:
        success = kg_service.create_job_node(job)
        if success:
            print(f"✅ Created node for job: {job.title}")
        else:
            print(f"❌ Failed to create node for job: {job.title}")
    
    # Create skill relationships
    print("🔗 Creating skill relationships...")
    relationships = create_skill_relationships()
    success = kg_service.create_skill_relationships(relationships)
    if success:
        print(f"✅ Created {len(relationships)} skill relationships")
    else:
        print("❌ Failed to create skill relationships")
    
    print("🎉 Database setup completed!")
    print("\n📊 Summary:")
    print(f"   - {len(sample_jobs)} jobs indexed in Elasticsearch")
    print(f"   - {len(sample_jobs)} job nodes created in Neo4j")
    print(f"   - {len(relationships)} skill relationships created")
    
    print("\n🌐 Access your application:")
    print("   - Frontend: http://localhost:3000")
    print("   - Backend API: http://localhost:8000")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - Elasticsearch: http://localhost:9200")
    print("   - Neo4j Browser: http://localhost:7474")

if __name__ == "__main__":
    setup_databases()
