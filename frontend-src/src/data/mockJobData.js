// Mock job data for testing UI/UX when backend is unavailable

const generateMockJobs = () => {
  const companies = [
    'Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix', 'Tesla', 'Uber',
    'Airbnb', 'Stripe', 'Salesforce', 'Adobe', 'Oracle', 'IBM', 'Intel', 'NVIDIA',
    'Spotify', 'Twitter', 'LinkedIn', 'GitHub', 'Shopify', 'Zoom', 'Slack', 'Dropbox'
  ];

  const jobTitles = [
    'Senior Software Engineer', 'Full Stack Developer', 'Backend Engineer', 'Frontend Developer',
    'DevOps Engineer', 'Machine Learning Engineer', 'Data Scientist', 'Product Manager',
    'Software Architect', 'Mobile Developer', 'Cloud Engineer', 'Security Engineer',
    'QA Engineer', 'Technical Lead', 'Engineering Manager', 'Research Scientist'
  ];

  const locations = [
    { city: 'San Francisco', state: 'CA', coordinates: { latitude: 37.7749, longitude: -122.4194 } },
    { city: 'New York', state: 'NY', coordinates: { latitude: 40.7128, longitude: -74.0060 } },
    { city: 'Seattle', state: 'WA', coordinates: { latitude: 47.6062, longitude: -122.3321 } },
    { city: 'Austin', state: 'TX', coordinates: { latitude: 30.2672, longitude: -97.7431 } },
    { city: 'Boston', state: 'MA', coordinates: { latitude: 42.3601, longitude: -71.0589 } },
    { city: 'Los Angeles', state: 'CA', coordinates: { latitude: 34.0522, longitude: -118.2437 } },
    { city: 'Chicago', state: 'IL', coordinates: { latitude: 41.8781, longitude: -87.6298 } },
    { city: 'Denver', state: 'CO', coordinates: { latitude: 39.7392, longitude: -104.9903 } }
  ];

  const skills = [
    'Python', 'JavaScript', 'React', 'Node.js', 'AWS', 'Docker', 'Kubernetes',
    'TypeScript', 'Java', 'Go', 'C++', 'SQL', 'MongoDB', 'PostgreSQL',
    'TensorFlow', 'PyTorch', 'Machine Learning', 'CI/CD', 'Git', 'REST APIs',
    'GraphQL', 'Microservices', 'System Design', 'Agile', 'Scrum'
  ];

  const jobTypes = ['full_time', 'part_time', 'contract', 'internship'];
  const experienceLevels = ['entry', 'mid', 'senior', 'executive'];

  const generateRandomDate = (daysAgo) => {
    const date = new Date();
    date.setDate(date.getDate() - daysAgo);
    return date.toISOString();
  };

  const generateSalary = () => {
    const baseSalaries = {
      entry: { min: 60000, max: 90000 },
      mid: { min: 90000, max: 140000 },
      senior: { min: 140000, max: 220000 },
      executive: { min: 200000, max: 350000 }
    };
    const level = experienceLevels[Math.floor(Math.random() * experienceLevels.length)];
    const range = baseSalaries[level];
    const min = range.min + Math.floor(Math.random() * (range.max - range.min) * 0.3);
    const max = min + Math.floor(Math.random() * (range.max - min));
    return { min_salary: min, max_salary: max };
  };

  const jobs = [];
  for (let i = 0; i < 20; i++) {
    const company = companies[Math.floor(Math.random() * companies.length)];
    const title = jobTitles[Math.floor(Math.random() * jobTitles.length)];
    const location = locations[Math.floor(Math.random() * locations.length)];
    const jobType = jobTypes[Math.floor(Math.random() * jobTypes.length)];
    const experienceLevel = experienceLevels[Math.floor(Math.random() * experienceLevels.length)];
    const salary = generateSalary();
    const remoteAllowed = Math.random() > 0.4;
    const visaSponsorship = Math.random() > 0.6;
    const postedDaysAgo = Math.floor(Math.random() * 30);
    
    // Generate random skills
    const numSkills = 5 + Math.floor(Math.random() * 8);
    const shuffledSkills = [...skills].sort(() => 0.5 - Math.random());
    const requiredSkills = shuffledSkills.slice(0, Math.floor(numSkills * 0.7));
    const preferredSkills = shuffledSkills.slice(Math.floor(numSkills * 0.7), numSkills);

    // Generate rerank score (for reranking mode)
    const rerankScore = 0.4 + Math.random() * 0.6; // Between 0.4 and 1.0

    jobs.push({
      id: `mock-job-${i + 1}`,
      title: title,
      description: `We are looking for a talented ${title} to join our ${company} team. You will work on cutting-edge projects, collaborate with world-class engineers, and help shape the future of technology. This role offers excellent growth opportunities and competitive compensation.`,
      company_name: company,
      location: {
        city: location.city,
        state: location.state,
        country: 'United States',
        coordinates: location.coordinates
      },
      job_type: jobType,
      experience_level: experienceLevel,
      salary: salary,
      benefits: [
        { name: 'Health Insurance', category: 'health' },
        { name: '401(k) Matching', category: 'retirement' },
        { name: 'Flexible PTO', category: 'work_life' },
        ...(visaSponsorship ? [{ name: 'Visa Sponsorship', category: 'visa' }] : [])
      ],
      required_skills: requiredSkills,
      preferred_skills: preferredSkills,
      responsibilities: [
        'Design and develop scalable software solutions',
        'Collaborate with cross-functional teams',
        'Write clean, maintainable code',
        'Participate in code reviews',
        'Contribute to technical documentation'
      ],
      requirements: [
        `Bachelor's degree in Computer Science or related field`,
        `Experience with ${requiredSkills[0]} and ${requiredSkills[1]}`,
        'Strong problem-solving skills',
        'Excellent communication abilities'
      ],
      posted_date: generateRandomDate(postedDaysAgo),
      application_deadline: generateRandomDate(-Math.floor(Math.random() * 60)),
      remote_allowed: remoteAllowed,
      visa_sponsorship: visaSponsorship,
      source_url: `https://careers.${company.toLowerCase()}.com/jobs/${i + 1}`,
      apply_url: `https://careers.${company.toLowerCase()}.com/apply/${i + 1}`,
      rerank_score: rerankScore,
      created_at: generateRandomDate(postedDaysAgo)
    });
  }

  return jobs;
};

// Generate mock search results
export const getMockSearchResults = (searchParams, useReranking = false) => {
  const mockJobs = generateMockJobs();
  
  // Filter jobs based on search params (simple mock filtering)
  let filteredJobs = [...mockJobs];
  
  if (searchParams.location) {
    const locationLower = searchParams.location.toLowerCase();
    filteredJobs = filteredJobs.filter(job => 
      job.location.city.toLowerCase().includes(locationLower) ||
      job.location.state.toLowerCase().includes(locationLower)
    );
  }
  
  if (searchParams.job_type) {
    filteredJobs = filteredJobs.filter(job => job.job_type === searchParams.job_type);
  }
  
  if (searchParams.experience_level) {
    filteredJobs = filteredJobs.filter(job => job.experience_level === searchParams.experience_level);
  }
  
  if (searchParams.remote_allowed !== undefined && searchParams.remote_allowed !== null) {
    filteredJobs = filteredJobs.filter(job => job.remote_allowed === searchParams.remote_allowed);
  }
  
  if (searchParams.visa_sponsorship !== undefined && searchParams.visa_sponsorship !== null) {
    filteredJobs = filteredJobs.filter(job => job.visa_sponsorship === searchParams.visa_sponsorship);
  }
  
  if (searchParams.min_salary) {
    filteredJobs = filteredJobs.filter(job => 
      job.salary && job.salary.max_salary >= searchParams.min_salary
    );
  }
  
  // Sort by rerank_score if reranking is enabled
  if (useReranking) {
    filteredJobs.sort((a, b) => (b.rerank_score || 0) - (a.rerank_score || 0));
  }
  
  // Pagination
  const page = searchParams.page || 1;
  const pageSize = searchParams.page_size || 20;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedJobs = filteredJobs.slice(startIndex, endIndex);
  
  // Calculate reranking statistics if reranking is enabled
  let rerankingStatistics = null;
  if (useReranking && paginatedJobs.length > 0) {
    const scores = paginatedJobs.map(job => job.rerank_score || 0);
    const averageScore = scores.reduce((a, b) => a + b, 0) / scores.length;
    const highQuality = scores.filter(s => s >= 0.8).length;
    const mediumQuality = scores.filter(s => s >= 0.6 && s < 0.8).length;
    const lowQuality = scores.filter(s => s < 0.6).length;
    
    rerankingStatistics = {
      average_score: averageScore,
      high_quality_matches: highQuality,
      medium_quality_matches: mediumQuality,
      low_quality_matches: lowQuality
    };
  }
  
  return {
    jobs: paginatedJobs,
    total_count: filteredJobs.length,
    page: page,
    page_size: pageSize,
    total_pages: Math.ceil(filteredJobs.length / pageSize),
    search_time_ms: 50 + Math.random() * 100, // Mock search time
    reranking_time_ms: useReranking ? 100 + Math.random() * 200 : null,
    reranking_statistics: rerankingStatistics,
    is_mock_data: true // Flag to indicate this is mock data
  };
};

// Mock delay to simulate API call
export const mockApiDelay = () => {
  return new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 500));
};

const mockJobData = {
  getMockSearchResults,
  mockApiDelay
};

export default mockJobData;

