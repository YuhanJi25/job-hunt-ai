import React, { useState } from 'react';
import { 
  Card, 
  Upload, 
  Button, 
  Typography, 
  Space, 
  Alert, 
  Row,
  Col,
  Tag,
  Progress,
  Divider,
  message
} from 'antd';
import { 
  InboxOutlined, 
  FileTextOutlined, 
  CheckCircleOutlined,
  BulbOutlined,
  ThunderboltOutlined,
  TeamOutlined
} from '@ant-design/icons';
import { useMutation } from 'react-query';
import { useNavigate } from 'react-router-dom';
import { uploadResume } from '../services/api';
import { useCandidate } from '../contexts/CandidateContext';

const { Title, Paragraph, Text } = Typography;
const { Dragger } = Upload;

const ResumeUploadPage = () => {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const navigate = useNavigate();
  const { updateCandidateProfile, updateResumeFile } = useCandidate();

  const uploadMutation = useMutation(uploadResume, {
    onSuccess: (data) => {
      setProcessing(false);
      // Store the candidate profile in context
      updateCandidateProfile(data);
      updateResumeFile(uploadedFile);
      message.success('Resume processed successfully!');
    },
    onError: (error) => {
      setProcessing(false);
      message.error(`Failed to process resume: ${error.message}`);
    },
  });

  const handleUpload = (file) => {
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
    
    setUploadedFile(file);
    setProcessing(true);
    uploadMutation.mutate(file);
    return false; // Prevent auto upload
  };

  const removeFile = () => {
    setUploadedFile(null);
    setProcessing(false);
  };

  const features = [
    {
      icon: <FileTextOutlined style={{ fontSize: '24px', color: '#1890ff' }} />,
      title: 'Smart Parsing',
      description: 'Extract skills, experience, and education automatically'
    },
    {
      icon: <BulbOutlined style={{ fontSize: '24px', color: '#52c41a' }} />,
      title: 'AI Analysis',
      description: 'Get insights and improvement suggestions'
    },
    {
      icon: <ThunderboltOutlined style={{ fontSize: '24px', color: '#faad14' }} />,
      title: 'Skill Mapping',
      description: 'Map your skills to job requirements'
    },
    {
      icon: <TeamOutlined style={{ fontSize: '24px', color: '#f5222d' }} />,
      title: 'Job Matching',
      description: 'Find relevant opportunities instantly'
    }
  ];

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      <Title level={2} style={{ textAlign: 'center', marginBottom: '32px' }}>
        📄 Upload Your Resume
      </Title>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card>
            <Title level={3} style={{ marginBottom: '16px' }}>
              Upload Resume File
            </Title>
            <Paragraph style={{ marginBottom: '24px' }}>
              Upload your resume in PDF or DOC format. Our AI will analyze your skills, 
              experience, and qualifications to provide personalized job recommendations.
            </Paragraph>

            {!uploadedFile ? (
              <Dragger
                name="resume"
                multiple={false}
                beforeUpload={handleUpload}
                accept=".pdf,.doc,.docx"
                style={{ padding: '40px' }}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
                </p>
                <p className="ant-upload-text" style={{ fontSize: '16px' }}>
                  Click or drag resume file to this area to upload
                </p>
                <p className="ant-upload-hint" style={{ fontSize: '14px' }}>
                  Support for PDF, DOC, and DOCX files up to 10MB
                </p>
              </Dragger>
            ) : (
              <Card>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <Text strong>{uploadedFile.name}</Text>
                      <br />
                      <Text type="secondary">
                        {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                      </Text>
                    </div>
                    <Button onClick={removeFile} type="link" danger>
                      Remove
                    </Button>
                  </div>
                  
                  {processing && (
                    <div>
                      <Text>Processing your resume...</Text>
                      <Progress percent={50} status="active" />
                    </div>
                  )}
                  
                  {uploadMutation.isSuccess && (
                    <Alert
                      message="Resume Processed Successfully!"
                      description="Your resume has been analyzed and your profile has been created."
                      type="success"
                      showIcon
                      icon={<CheckCircleOutlined />}
                    />
                  )}
                  
                  {uploadMutation.isError && (
                    <Alert
                      message="Processing Failed"
                      description={uploadMutation.error?.message || 'An error occurred while processing your resume.'}
                      type="error"
                      showIcon
                    />
                  )}
                </Space>
              </Card>
            )}
          </Card>

          {uploadMutation.isSuccess && uploadMutation.data && (
            <Card style={{ marginTop: '24px' }}>
              <Title level={3}>Resume Analysis Results</Title>
              
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={12}>
                  <Card size="small">
                    <Title level={5}>Extracted Skills</Title>
                    <div>
                      {uploadMutation.data.extracted_skills?.slice(0, 10).map((skill, index) => (
                        <Tag key={index} color="blue" style={{ margin: '2px' }}>
                          {skill}
                        </Tag>
                      ))}
                      {uploadMutation.data.extracted_skills?.length > 10 && (
                        <Tag>+{uploadMutation.data.extracted_skills.length - 10} more</Tag>
                      )}
                    </div>
                  </Card>
                </Col>
                
                <Col xs={24} sm={12}>
                  <Card size="small">
                    <Title level={5}>Experience Summary</Title>
                    <Paragraph ellipsis={{ rows: 3 }}>
                      {uploadMutation.data.experience_summary || 'No experience found'}
                    </Paragraph>
                  </Card>
                </Col>
              </Row>

              <Divider />

              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Title level={2} style={{ color: '#1890ff', margin: 0 }}>
                      {uploadMutation.data.extracted_skills?.length || 0}
                    </Title>
                    <Text type="secondary">Skills Found</Text>
                  </div>
                </Col>
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Title level={2} style={{ color: '#52c41a', margin: 0 }}>
                      {Object.keys(uploadMutation.data.skill_categories || {}).length}
                    </Title>
                    <Text type="secondary">Skill Categories</Text>
                  </div>
                </Col>
                <Col xs={24} sm={8}>
                  <div style={{ textAlign: 'center' }}>
                    <Title level={2} style={{ color: '#faad14', margin: 0 }}>
                      {uploadMutation.data.extracted_experience?.length || 0}
                    </Title>
                    <Text type="secondary">Experience Items</Text>
                  </div>
                </Col>
              </Row>

              <div style={{ marginTop: '24px', textAlign: 'center' }}>
                <Button 
                  type="primary" 
                  size="large" 
                  onClick={() => navigate('/recommendations')}
                >
                  Get Job Recommendations
                </Button>
              </div>
            </Card>
          )}
        </Col>

        <Col xs={24} lg={8}>
          <Card>
            <Title level={4}>What We Analyze</Title>
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              {features.map((feature, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'flex-start' }}>
                  <div style={{ marginRight: '12px', marginTop: '4px' }}>
                    {feature.icon}
                  </div>
                  <div>
                    <Title level={5} style={{ margin: 0, marginBottom: '4px' }}>
                      {feature.title}
                    </Title>
                    <Text type="secondary">{feature.description}</Text>
                  </div>
                </div>
              ))}
            </Space>
          </Card>

          <Card style={{ marginTop: '24px' }}>
            <Title level={4}>Tips for Better Results</Title>
            <ul style={{ paddingLeft: '20px' }}>
              <li>Use a clear, well-formatted resume</li>
              <li>Include specific technical skills</li>
              <li>List your work experience with descriptions</li>
              <li>Include education and certifications</li>
              <li>Use standard job titles and industry terms</li>
            </ul>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ResumeUploadPage;
