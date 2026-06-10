import React, { useEffect, useRef, useState } from 'react';
import { Card, Row, Col, Typography, Button, Space, Statistic, Avatar, Divider, Tag } from 'antd';
import { Link } from 'react-router-dom';
import { 
  SearchOutlined, 
  UploadOutlined, 
  HeartOutlined, 
  RocketOutlined,
  BulbOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  BookOutlined,
  GlobalOutlined,
  StarFilled,
  ArrowRightOutlined,
  ApartmentOutlined,
  TrophyOutlined,
  EnvironmentOutlined,
  DollarOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import './HomePage.css';

const { Title, Paragraph, Text } = Typography;

// Custom hook for scroll animations
const useScrollAnimation = () => {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const currentRef = ref.current;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
      }
    );

    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, []);

  return [ref, isVisible];
};

const HomePage = () => {
  const features = [
    {
      icon: <SearchOutlined style={{ fontSize: '32px', color: '#1890ff' }} />,
      title: 'AI-Powered Search',
      description: 'Find jobs using natural language queries with advanced semantic understanding.'
    },
    {
      icon: <UploadOutlined style={{ fontSize: '32px', color: '#52c41a' }} />,
      title: 'Smart Resume Analysis',
      description: 'Upload your resume and get intelligent job matching based on your skills and experience.'
    },
    {
      icon: <HeartOutlined style={{ fontSize: '32px', color: '#f5222d' }} />,
      title: 'Personalized Recommendations',
      description: 'Get job recommendations tailored to your profile and career goals.'
    },
    {
      icon: <BulbOutlined style={{ fontSize: '32px', color: '#faad14' }} />,
      title: 'Knowledge Graph Matching',
      description: 'Leverage advanced knowledge graphs to understand skill relationships and career paths.'
    }
  ];

  const stats = [
    { title: 'Jobs Indexed', value: '10,000+', icon: <RocketOutlined /> },
    { title: 'Skills Mapped', value: '5,000+', icon: <ThunderboltOutlined /> },
    { title: 'Companies', value: '500+', icon: <TeamOutlined /> },
    { title: 'Success Rate', value: '95%', icon: <HeartOutlined /> }
  ];

  const userTypes = [
    {
      icon: <ApartmentOutlined style={{ fontSize: '48px', color: '#1890ff' }} />,
      title: 'Associations',
      description: 'Connect your members with tailored job opportunities and career development resources.',
      color: '#1890ff'
    },
    {
      icon: <GlobalOutlined style={{ fontSize: '48px', color: '#52c41a' }} />,
      title: 'Non-Profits',
      description: 'Find passionate professionals who align with your mission and values.',
      color: '#52c41a'
    },
    {
      icon: <BookOutlined style={{ fontSize: '48px', color: '#faad14' }} />,
      title: 'Educational Institutions',
      description: 'Help students and alumni discover career paths and job opportunities.',
      color: '#faad14'
    }
  ];

  const testimonials = [
    {
      name: 'Sarah Johnson',
      role: 'Software Engineer',
      company: 'Tech Corp',
      avatar: 'SJ',
      rating: 5,
      text: 'Found my dream job in just 2 weeks! The AI matching was incredibly accurate.'
    },
    {
      name: 'Michael Chen',
      role: 'Data Scientist',
      company: 'Data Analytics Inc',
      avatar: 'MC',
      rating: 5,
      text: 'The personalized recommendations saved me hours of searching. Highly recommend!'
    },
    {
      name: 'Emily Rodriguez',
      role: 'UX Designer',
      company: 'Design Studio',
      avatar: 'ER',
      rating: 5,
      text: 'Best job search platform I\'ve used. The match percentage breakdown is so helpful.'
    }
  ];

  const partners = [
    'Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix'
  ];

  const matchBreakdown = [
    { label: 'Skills Match', value: 92, color: '#52c41a' },
    { label: 'Experience Level', value: 88, color: '#52c41a' },
    { label: 'Location Preference', value: 95, color: '#52c41a' },
    { label: 'Salary Range', value: 85, color: '#faad14' },
    { label: 'Company Culture', value: 90, color: '#52c41a' }
  ];

  const demoJobs = [
    {
      id: 1,
      title: 'Senior Software Engineer',
      company: 'TechCorp Inc.',
      location: 'San Francisco, CA',
      salary: '$120k - $180k',
      type: 'Full-time',
      remote: true,
      matchScore: 95,
      tags: ['React', 'Node.js', 'AWS'],
      postedDate: '2 days ago',
      bgColor: '#e5dbfa'
    },
    {
      id: 2,
      title: 'Product Manager',
      company: 'Innovation Labs',
      location: 'New York, NY',
      salary: '$130k - $160k',
      type: 'Full-time',
      remote: false,
      matchScore: 88,
      tags: ['Product Strategy', 'Agile', 'Data Analysis'],
      postedDate: '1 week ago',
      bgColor: '#fbe2f4'
    },
    {
      id: 3,
      title: 'UX Designer',
      company: 'Design Studio Pro',
      location: 'Austin, TX',
      salary: '$90k - $130k',
      type: 'Full-time',
      remote: true,
      matchScore: 92,
      tags: ['Figma', 'UI/UX', 'Design Systems'],
      postedDate: '3 days ago',
      bgColor: '#ffe1cc'
    },
    {
      id: 4,
      title: 'Data Scientist',
      company: 'AI Solutions',
      location: 'Seattle, WA',
      salary: '$140k - $190k',
      type: 'Full-time',
      remote: true,
      matchScore: 90,
      tags: ['Python', 'Machine Learning', 'TensorFlow'],
      postedDate: '5 days ago',
      bgColor: '#d4f6ed'
    },
    {
      id: 5,
      title: 'DevOps Engineer',
      company: 'Cloud Systems',
      location: 'Remote',
      salary: '$110k - $150k',
      type: 'Full-time',
      remote: true,
      matchScore: 87,
      tags: ['Docker', 'Kubernetes', 'CI/CD'],
      postedDate: '1 day ago',
      bgColor: '#e5dbfa'
    },
    {
      id: 6,
      title: 'Marketing Manager',
      company: 'Growth Co',
      location: 'Boston, MA',
      salary: '$100k - $140k',
      type: 'Full-time',
      remote: false,
      matchScore: 85,
      tags: ['Digital Marketing', 'SEO', 'Analytics'],
      postedDate: '4 days ago',
      bgColor: '#fbe2f4'
    }
  ];

  const [matchRef, matchVisible] = useScrollAnimation();
  const [featuresRef, featuresVisible] = useScrollAnimation();
  const [builtForRef, builtForVisible] = useScrollAnimation();
  const [demoJobsRef, demoJobsVisible] = useScrollAnimation();
  const [testimonialsRef, testimonialsVisible] = useScrollAnimation();

  return (
    <div className="homepage-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-content">
          <div className="hero-text">
            <Title level={1} className="hero-title">
              Find Your Perfect Job Match with AI
            </Title>
            <Paragraph className="hero-subtitle">
              Our intelligent platform uses advanced AI and knowledge graphs to connect you 
              with opportunities that truly match your skills, experience, and career goals.
            </Paragraph>
            <Space size="large" className="hero-cta">
              <Button 
                type="primary" 
                size="large" 
                icon={<SearchOutlined />}
                className="cta-button-primary"
              >
                <Link to="/search" style={{ color: 'white' }}>Start Searching</Link>
              </Button>
              <Button 
                size="large" 
                icon={<UploadOutlined />}
                className="cta-button-secondary"
              >
                <Link to="/upload-resume">Upload Resume</Link>
              </Button>
            </Space>
          </div>
          <div className="hero-visual">
            <div className="ai-matching-visual">
              <div className="matching-circle">
                <div className="match-percentage">92%</div>
                <div className="match-label">Match</div>
              </div>
              <div className="connecting-lines">
                <div className="line line-1"></div>
                <div className="line line-2"></div>
                <div className="line line-3"></div>
              </div>
              <div className="job-icons">
                <div className="job-icon icon-1">💼</div>
                <div className="job-icon icon-2">🎯</div>
                <div className="job-icon icon-3">🚀</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="stats-section">
        <Row gutter={[24, 24]} justify="center">
          {stats.map((stat, index) => (
            <Col xs={12} sm={6} key={index}>
              <Card className="stat-card">
                <Statistic
                  title={stat.title}
                  value={stat.value}
                  prefix={stat.icon}
                  valueStyle={{ color: '#1890ff', fontSize: '28px', fontWeight: 'bold' }}
                />
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* Match Breakdown Section */}
      <section className="match-breakdown-section gradient-bg-purple" ref={matchRef}>
        <div className={`section-header animate-fade-in ${matchVisible ? 'visible' : ''}`}>
          <Title level={2} className="section-title">
            See Your Match Breakdown
          </Title>
          <Paragraph className="section-description">
            Understand exactly how well each job matches your profile
          </Paragraph>
        </div>
        <Card className={`match-breakdown-card animate-fade-in ${matchVisible ? 'visible' : ''}`}>
          <div className="match-breakdown-header">
            <div className="match-example-title">
              <Title level={3} style={{ margin: 0 }}>Risk Analyst Position</Title>
              <Text type="secondary">Example Match Analysis</Text>
            </div>
            <div className="overall-match-score">
              <div className="match-score-large">92%</div>
              <Text type="secondary">Overall Match</Text>
            </div>
          </div>
          <Divider />
          <Row gutter={[24, 16]}>
            {matchBreakdown.map((item, index) => (
              <Col xs={24} sm={12} md={8} key={index}>
                <div className="match-item">
                  <div className="match-item-header">
                    <Text strong>{item.label}</Text>
                    <Text strong style={{ color: item.color, fontSize: '16px' }}>
                      {item.value}%
                    </Text>
                  </div>
                  <div className="match-progress-bar">
                    <div 
                      className="match-progress-fill" 
                      style={{ 
                        width: `${item.value}%`, 
                        backgroundColor: item.color 
                      }}
                    ></div>
                  </div>
                </div>
              </Col>
            ))}
          </Row>
        </Card>
      </section>

      {/* Features Section */}
      <section className="features-section gradient-bg-pink" ref={featuresRef}>
        <div className={`section-header animate-fade-in ${featuresVisible ? 'visible' : ''}`}>
          <Title level={2} className="section-title">
            How It Works
          </Title>
          <Paragraph className="section-description">
            Powerful features designed to make your job search effortless
          </Paragraph>
        </div>
        <Row gutter={[24, 24]} justify="center">
          {features.map((feature, index) => (
            <Col xs={24} sm={12} lg={6} key={index}>
              <Card 
                className={`feature-card animate-fade-in ${featuresVisible ? 'visible' : ''}`}
                style={{ animationDelay: `${index * 0.1}s` }}
                hoverable
              >
                <div className="feature-icon">{feature.icon}</div>
                <Title level={4} className="feature-title">
                  {feature.title}
                </Title>
                <Paragraph className="feature-description">
                  {feature.description}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* Demo Jobs Section */}
      <section className="demo-jobs-section gradient-bg-mint" ref={demoJobsRef}>
        <div className={`section-header animate-fade-in ${demoJobsVisible ? 'visible' : ''}`}>
          <Title level={2} className="section-title">
            Explore Opportunities
          </Title>
          <Paragraph className="section-description">
            See the type of jobs you could discover on our platform
          </Paragraph>
        </div>
        <Row gutter={[24, 24]} justify="center">
          {demoJobs.map((job, index) => (
            <Col xs={24} sm={12} lg={8} key={job.id}>
              <Card 
                className={`demo-job-card animate-fade-in ${demoJobsVisible ? 'visible' : ''}`}
                style={{ 
                  backgroundColor: job.bgColor,
                  animationDelay: `${index * 0.1}s`
                }}
                hoverable
              >
                <div className="job-card-header">
                  <div className="company-logo-demo">
                    {job.company.charAt(0)}
                  </div>
                  <div className="match-badge">
                    <span className="match-score">{job.matchScore}%</span>
                    <span className="match-label">Match</span>
                  </div>
                </div>
                <Title level={4} className="job-title-demo">{job.title}</Title>
                <Text className="company-name-demo">{job.company}</Text>
                <div className="job-details-demo">
                  <div className="job-detail-item">
                    <EnvironmentOutlined />
                    <Text>{job.location}</Text>
                  </div>
                  <div className="job-detail-item">
                    <DollarOutlined />
                    <Text>{job.salary}</Text>
                  </div>
                  <div className="job-detail-item">
                    <ClockCircleOutlined />
                    <Text>{job.postedDate}</Text>
                  </div>
                </div>
                <div className="job-tags-demo">
                  {job.tags.map((tag, idx) => (
                    <Tag key={idx} className="job-tag-demo">{tag}</Tag>
                  ))}
                  {job.remote && <Tag color="green">Remote</Tag>}
                </div>
                <Button type="primary" className="job-details-btn" block>
                  View Details
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
        <div className="view-all-jobs-btn-container">
          <Button 
            type="primary" 
            size="large" 
            icon={<SearchOutlined />}
            className="view-all-jobs-btn"
          >
            <Link to="/search" style={{ color: 'white' }}>View All Jobs</Link>
          </Button>
        </div>
      </section>

      {/* User Types Section */}
      <section className="user-types-section gradient-bg-peach" ref={builtForRef}>
        <div className={`section-header animate-fade-in ${builtForVisible ? 'visible' : ''}`}>
          <Title level={2} className="section-title">
            Built for Everyone
          </Title>
          <Paragraph className="section-description">
            Tailored solutions for different organizations and communities
          </Paragraph>
        </div>
        <Row gutter={[32, 32]} justify="center">
          {userTypes.map((type, index) => (
            <Col xs={24} md={8} key={index}>
              <Card 
                className={`user-type-card animate-fade-in ${builtForVisible ? 'visible' : ''}`}
                style={{ animationDelay: `${index * 0.1}s` }}
                hoverable
              >
                <div className="user-type-icon" style={{ color: type.color }}>
                  {type.icon}
                </div>
                <Title level={3} className="user-type-title">
                  {type.title}
                </Title>
                <Paragraph className="user-type-description">
                  {type.description}
                </Paragraph>
                <Button type="link" className="user-type-link">
                  Learn More <ArrowRightOutlined />
                </Button>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* Testimonials Section */}
      <section className="testimonials-section gradient-bg-purple" ref={testimonialsRef}>
        <div className={`section-header animate-fade-in ${testimonialsVisible ? 'visible' : ''}`}>
          <Title level={2} className="section-title">
            What Our Users Say
          </Title>
          <Paragraph className="section-description">
            Join thousands of successful job seekers
          </Paragraph>
        </div>
        <Row gutter={[24, 24]} justify="center">
          {testimonials.map((testimonial, index) => (
            <Col xs={24} md={8} key={index}>
              <Card 
                className={`testimonial-card animate-fade-in ${testimonialsVisible ? 'visible' : ''}`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="testimonial-header">
                  <Avatar size={64} className="testimonial-avatar">
                    {testimonial.avatar}
                  </Avatar>
                  <div className="testimonial-info">
                    <Text strong>{testimonial.name}</Text>
                    <Text type="secondary" className="testimonial-role">
                      {testimonial.role}
                    </Text>
                    <Text type="secondary" className="testimonial-company">
                      {testimonial.company}
                    </Text>
                  </div>
                </div>
                <div className="testimonial-rating">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <StarFilled key={i} style={{ color: '#faad14' }} />
                  ))}
                </div>
                <Paragraph className="testimonial-text">
                  "{testimonial.text}"
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* Partners Section */}
      <section className="partners-section">
        <div className="section-header">
          <Title level={2} className="section-title">
            Trusted by Leading Companies
          </Title>
        </div>
        <div className="partners-logos">
          {partners.map((partner, index) => (
            <div key={index} className="partner-logo">
              <Text strong style={{ fontSize: '18px', color: '#666' }}>
                {partner}
              </Text>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <Card className="cta-card">
          <div className="cta-content">
            <TrophyOutlined className="cta-icon" />
            <Title level={2} className="cta-title">
              Ready to Find Your Perfect Job?
            </Title>
            <Paragraph className="cta-description">
              Join thousands of job seekers who have found their dream positions using our AI-powered platform.
            </Paragraph>
            <Space size="large" className="cta-buttons">
              <Button 
                type="primary" 
                size="large" 
                icon={<SearchOutlined />}
                className="cta-button-primary"
              >
                <Link to="/search" style={{ color: 'white' }}>Search Jobs Now</Link>
              </Button>
              <Button 
                size="large" 
                icon={<UploadOutlined />}
                className="cta-button-secondary"
              >
                <Link to="/upload-resume">Upload Your Resume</Link>
              </Button>
            </Space>
          </div>
        </Card>
      </section>
    </div>
  );
};

export default HomePage;
