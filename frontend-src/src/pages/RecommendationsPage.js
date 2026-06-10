import React, { useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Button, 
  Space, 
  Tag, 
  Row, 
  Col, 
  Alert,
  Spin,
  Progress,
  Upload,
  message
} from 'antd';
import { 
  HeartOutlined, 
  UploadOutlined, 
  StarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useQuery, useMutation } from 'react-query';
import { getJobRecommendations, uploadResume } from '../services/api';
import { useCandidate } from '../contexts/CandidateContext';

const { Title, Paragraph, Text } = Typography;

const RecommendationsPage = () => {
  const { candidateProfile, updateCandidateProfile, updateResumeFile } = useCandidate();

  const uploadMutation = useMutation(uploadResume, {
    onSuccess: (data) => {
      updateCandidateProfile(data);
      message.success('Resume processed! Getting recommendations...');
    },
    onError: (error) => {
      message.error(`Failed to process resume: ${error.message}`);
    },
  });

  // Auto-fetch recommendations if candidate profile exists
  useEffect(() => {
    if (candidateProfile?.candidate) {
      message.info('Using your uploaded resume to get recommendations...');
    }
  }, [candidateProfile]);

  const { data: recommendations, isLoading, error } = useQuery(
    ['recommendations', candidateProfile?.candidate?.id],
    () => getJobRecommendations(candidateProfile?.candidate),
    {
      enabled: !!candidateProfile?.candidate,
      retry: 1
    }
  );

  const handleResumeUpload = (file) => {
    const isPdf = file.type === 'application/pdf';
    const isDoc = file.type === 'application/msword' || 
                  file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    
    if (!isPdf && !isDoc) {
      message.error('You can only upload PDF or DOC files!');
      return false;
    }
    
    const isLt10M = file.size / 1024 / 1024 < 10;
    if (!isLt10M) {
      message.error('File must be smaller than 10MB!');
      return false;
    }
    
    updateResumeFile(file);
    uploadMutation.mutate(file);
    return false;
  };

  const getMatchScoreColor = (score) => {
    if (score >= 0.8) return '#52c41a';
    if (score >= 0.6) return '#faad14';
    if (score >= 0.4) return '#fa8c16';
    return '#f5222d';
  };


  const getOverallFitColor = (fit) => {
    switch (fit) {
      case 'excellent': return '#52c41a';
      case 'good': return '#faad14';
      case 'fair': return '#fa8c16';
      case 'poor': return '#f5222d';
      default: return '#d9d9d9';
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <Title level={2} style={{ textAlign: 'center', marginBottom: '32px' }}>
        💡 Personalized Job Recommendations
      </Title>

      {!candidateProfile ? (
        <Card style={{ marginBottom: '24px' }}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <UploadOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: '16px' }} />
            <Title level={3}>Upload Your Resume to Get Started</Title>
            <Paragraph style={{ marginBottom: '24px' }}>
              Upload your resume to get personalized job recommendations based on your skills, 
              experience, and career goals.
            </Paragraph>
            
            <Upload
              beforeUpload={handleResumeUpload}
              showUploadList={false}
              accept=".pdf,.doc,.docx"
            >
              <Button 
                type="primary" 
                size="large" 
                icon={<UploadOutlined />}
                loading={uploadMutation.isLoading}
              >
                Upload Resume
              </Button>
            </Upload>
          </div>
        </Card>
      ) : (
        <Card style={{ marginBottom: '24px' }}>
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <CheckCircleOutlined style={{ fontSize: '24px', color: '#52c41a', marginBottom: '8px' }} />
            <Title level={4} style={{ color: '#52c41a', marginBottom: '8px' }}>
              Resume Processed Successfully!
            </Title>
            <Paragraph style={{ marginBottom: '16px' }}>
              Using resume for <strong>{candidateProfile.candidate.name}</strong> to generate recommendations.
            </Paragraph>
            <Upload
              beforeUpload={handleResumeUpload}
              showUploadList={false}
              accept=".pdf,.doc,.docx"
            >
              <Button 
                size="small" 
                icon={<UploadOutlined />}
                loading={uploadMutation.isLoading}
              >
                Upload Different Resume
              </Button>
            </Upload>
          </div>
        </Card>
      )}

      {uploadMutation.isLoading && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <Title level={4} style={{ marginTop: '16px' }}>
              Processing Your Resume...
            </Title>
            <Paragraph>Analyzing your skills and experience to find the best matches.</Paragraph>
          </div>
        </Card>
      )}

      {candidateProfile && (
        <Card style={{ marginBottom: '24px' }}>
          <Title level={3}>Your Profile</Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <div style={{ textAlign: 'center' }}>
                <Title level={2} style={{ color: '#1890ff', margin: 0 }}>
                  {candidateProfile.skills?.length || 0}
                </Title>
                <Text type="secondary">Skills Identified</Text>
              </div>
            </Col>
            <Col xs={24} sm={8}>
              <div style={{ textAlign: 'center' }}>
                <Title level={2} style={{ color: '#52c41a', margin: 0 }}>
                  {candidateProfile.experience?.length || 0}
                </Title>
                <Text type="secondary">Work Experiences</Text>
              </div>
            </Col>
            <Col xs={24} sm={8}>
              <div style={{ textAlign: 'center' }}>
                <Title level={2} style={{ color: '#faad14', margin: 0 }}>
                  {candidateProfile.education?.length || 0}
                </Title>
                <Text type="secondary">Education Items</Text>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {isLoading && candidateProfile && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <Spin size="large" />
            <Title level={4} style={{ marginTop: '16px' }}>
              Finding Your Perfect Matches...
            </Title>
            <Paragraph>Analyzing thousands of jobs to find the best opportunities for you.</Paragraph>
          </div>
        </Card>
      )}

      {error && (
        <Alert
          message="Error Loading Recommendations"
          description="There was an error loading your job recommendations. Please try again."
          type="error"
          showIcon
        />
      )}

      {recommendations && recommendations.length > 0 && (
        <div>
          <div style={{ marginBottom: '24px', textAlign: 'center' }}>
            <Title level={3}>
              Found {recommendations.length} Job Recommendations
            </Title>
            <Paragraph>
              These jobs are ranked by how well they match your profile and preferences.
            </Paragraph>
          </div>

          {recommendations.map((match, index) => (
            <Card 
              key={match.job_id} 
              style={{ marginBottom: '16px' }}
              hoverable
            >
              <Row gutter={[24, 16]}>
                <Col xs={24} lg={16}>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <Title level={4} style={{ margin: 0, marginBottom: '4px' }}>
                          Job #{index + 1}
                        </Title>
                        <Text type="secondary">Job ID: {match.job_id}</Text>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <Tag 
                          color={getOverallFitColor(match.overall_fit)}
                          style={{ fontSize: '12px', padding: '4px 12px' }}
                        >
                          {match.overall_fit.toUpperCase()} FIT
                        </Tag>
                        <div style={{ marginTop: '8px' }}>
                          <Text strong style={{ color: getMatchScoreColor(match.match_score) }}>
                            {Math.round(match.match_score * 100)}% Match
                          </Text>
                        </div>
                      </div>
                    </div>
                  </div>

                  <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12}>
                      <Card size="small" title="Match Analysis">
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text>Skills Match:</Text>
                            <Text strong>{Math.round(match.match_score * 100)}%</Text>
                          </div>
                          <Progress 
                            percent={Math.round(match.match_score * 100)} 
                            size="small"
                            strokeColor={getMatchScoreColor(match.match_score)}
                          />
                          
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text>Experience Match:</Text>
                            <Text strong>{Math.round(match.experience_match * 100)}%</Text>
                          </div>
                          <Progress 
                            percent={Math.round(match.experience_match * 100)} 
                            size="small"
                            strokeColor={getMatchScoreColor(match.experience_match)}
                          />
                        </Space>
                      </Card>
                    </Col>
                    
                    <Col xs={24} sm={12}>
                      <Card size="small" title="Requirements Check">
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Text>Location Match:</Text>
                            {match.location_match ? (
                              <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            ) : (
                              <CloseCircleOutlined style={{ color: '#f5222d' }} />
                            )}
                          </div>
                          
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Text>Salary Match:</Text>
                            {match.salary_match ? (
                              <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            ) : (
                              <CloseCircleOutlined style={{ color: '#f5222d' }} />
                            )}
                          </div>
                          
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <Text>Visa Sponsorship:</Text>
                            {match.visa_match ? (
                              <CheckCircleOutlined style={{ color: '#52c41a' }} />
                            ) : (
                              <CloseCircleOutlined style={{ color: '#f5222d' }} />
                            )}
                          </div>
                        </Space>
                      </Card>
                    </Col>
                  </Row>

                  {match.matching_skills && match.matching_skills.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                      <Text strong>Matching Skills:</Text>
                      <div style={{ marginTop: '8px' }}>
                        {match.matching_skills.slice(0, 8).map((skill) => (
                          <Tag key={skill} color="green" style={{ margin: '2px' }}>
                            {skill}
                          </Tag>
                        ))}
                        {match.matching_skills.length > 8 && (
                          <Tag>+{match.matching_skills.length - 8} more</Tag>
                        )}
                      </div>
                    </div>
                  )}

                  {match.missing_skills && match.missing_skills.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                      <Text strong>Skills to Develop:</Text>
                      <div style={{ marginTop: '8px' }}>
                        {match.missing_skills.slice(0, 5).map((skill) => (
                          <Tag key={skill} color="orange" style={{ margin: '2px' }}>
                            {skill}
                          </Tag>
                        ))}
                        {match.missing_skills.length > 5 && (
                          <Tag>+{match.missing_skills.length - 5} more</Tag>
                        )}
                      </div>
                    </div>
                  )}
                </Col>
                
                <Col xs={24} lg={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Space direction="vertical" size="large" style={{ width: '100%' }}>
                      <div>
                        <Title level={2} style={{ 
                          color: getMatchScoreColor(match.match_score),
                          margin: 0
                        }}>
                          {Math.round(match.match_score * 100)}%
                        </Title>
                        <Text type="secondary">Overall Match</Text>
                      </div>
                      
                      <Button 
                        type="primary" 
                        size="large" 
                        icon={<StarOutlined />}
                        style={{ width: '100%' }}
                      >
                        View Job Details
                      </Button>
                      
                      <Button 
                        size="large" 
                        icon={<HeartOutlined />}
                        style={{ width: '100%' }}
                      >
                        Save Job
                      </Button>
                    </Space>
                  </div>
                </Col>
              </Row>
            </Card>
          ))}
        </div>
      )}

      {recommendations && recommendations.length === 0 && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <InfoCircleOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: '16px' }} />
            <Title level={3}>No Recommendations Found</Title>
            <Paragraph>
              We couldn't find any jobs that match your current profile. 
              Try uploading a more detailed resume or adjusting your search criteria.
            </Paragraph>
            <Space>
              <Button type="primary" href="/upload-resume">
                Upload New Resume
              </Button>
              <Button href="/search">
                Browse All Jobs
              </Button>
            </Space>
          </div>
        </Card>
      )}
    </div>
  );
};

export default RecommendationsPage;
