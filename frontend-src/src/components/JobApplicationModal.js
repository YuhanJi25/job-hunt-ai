import React, { useState } from 'react';
import { 
  Modal, 
  Form, 
  Input, 
  Button, 
  Typography, 
  Space, 
  Alert,
  Row,
  Col,
  Upload,
  message,
  Divider,
  Card
} from 'antd';
import { 
  UserOutlined, 
  MailOutlined, 
  PhoneOutlined,
  FileTextOutlined,
  SendOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { applyToJob } from '../services/api';

const { Title, Text } = Typography;
const { TextArea } = Input;

const JobApplicationModal = ({ 
  visible, 
  onClose, 
  job, 
  onApplicationSubmitted 
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resumeFile, setResumeFile] = useState(null);
  const { user, token, isAuthenticated } = useAuth();

  const handleSubmit = async (values) => {
    if (!isAuthenticated()) {
      message.error('Please login to apply for jobs');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const applicationData = {
        ...values,
        resume_file: resumeFile?.name,
        applied_at: new Date().toISOString(),
        user_info: {
          user_id: user.id,
          email: user.email,
          name: `${user.first_name} ${user.last_name}`
        }
      };

      await applyToJob(job.id, applicationData, token);
      
      message.success('Application submitted successfully!');
      onApplicationSubmitted();
      onClose();
      form.resetFields();
      setResumeFile(null);
      
    } catch (err) {
      setError(err.message || 'Failed to submit application. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResumeUpload = (file) => {
    const isPdf = file.type === 'application/pdf';
    const isDoc = file.type === 'application/msword' || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    
    if (!isPdf && !isDoc) {
      message.error('You can only upload PDF or DOC files!');
      return false;
    }
    
    const isLt10M = file.size / 1024 / 1024 < 10;
    if (!isLt10M) {
      message.error('File must be smaller than 10MB!');
      return false;
    }
    
    setResumeFile(file);
    message.success('Resume uploaded successfully!');
    return false; // Prevent auto upload
  };

  const handleClose = () => {
    form.resetFields();
    setResumeFile(null);
    setError(null);
    onClose();
  };

  return (
    <Modal
      title={null}
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={800}
      style={{ top: 20 }}
      bodyStyle={{ 
        padding: 0,
        background: 'transparent'
      }}
      maskStyle={{
        background: 'rgba(0, 0, 0, 0.7)',
        backdropFilter: 'blur(10px)'
      }}
      closable={false}
    >
      <div style={{
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(20px)',
        borderRadius: '20px',
        padding: '32px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
        border: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        {/* Header */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '24px'
        }}>
          <div>
            <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
              Apply for Position
            </Title>
            <Title level={4} style={{ margin: 0, color: '#666' }}>
              {job?.title} at {job?.company_name}
            </Title>
          </div>
          <Button 
            type="text" 
            icon={<CloseOutlined />} 
            onClick={handleClose}
            style={{ fontSize: '20px' }}
          />
        </div>

        {error && (
          <Alert
            message="Application Error"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: '24px' }}
          />
        )}

        {/* Job Summary */}
        <Card 
          size="small" 
          style={{ 
            marginBottom: '24px',
            background: 'rgba(24, 144, 255, 0.05)',
            border: '1px solid rgba(24, 144, 255, 0.1)'
          }}
        >
          <Row gutter={[16, 8]}>
            <Col span={12}>
              <Text strong>Location:</Text> {job?.location?.city}, {job?.location?.state}
            </Col>
            <Col span={12}>
              <Text strong>Job Type:</Text> {job?.job_type?.replace('_', ' ').toUpperCase()}
            </Col>
            <Col span={12}>
              <Text strong>Experience Level:</Text> {job?.experience_level?.replace('_', ' ').toUpperCase()}
            </Col>
            <Col span={12}>
              <Text strong>Remote:</Text> {job?.remote_allowed ? 'Yes' : 'No'}
            </Col>
          </Row>
        </Card>

        <Form
          form={form}
          name="jobApplication"
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
          initialValues={{
            email: user?.email || '',
            first_name: user?.first_name || '',
            last_name: user?.last_name || ''
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="first_name"
                label="First Name"
                rules={[
                  { required: true, message: 'Please enter your first name!' }
                ]}
              >
                <Input 
                  prefix={<UserOutlined />} 
                  placeholder="John"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="last_name"
                label="Last Name"
                rules={[
                  { required: true, message: 'Please enter your last name!' }
                ]}
              >
                <Input 
                  prefix={<UserOutlined />} 
                  placeholder="Doe"
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="email"
                label="Email Address"
                rules={[
                  { required: true, message: 'Please enter your email!' },
                  { type: 'email', message: 'Please enter a valid email!' }
                ]}
              >
                <Input 
                  prefix={<MailOutlined />} 
                  placeholder="john.doe@example.com"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="Phone Number"
                rules={[
                  { required: true, message: 'Please enter your phone number!' }
                ]}
              >
                <Input 
                  prefix={<PhoneOutlined />} 
                  placeholder="+1 (555) 123-4567"
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="cover_letter"
            label="Cover Letter"
            rules={[
              { required: true, message: 'Please write a cover letter!' },
              { min: 100, message: 'Cover letter must be at least 100 characters!' }
            ]}
          >
            <TextArea 
              rows={6}
              placeholder="Tell us why you're interested in this position and what makes you a great fit..."
              style={{ resize: 'vertical' }}
            />
          </Form.Item>

          <Form.Item
            name="resume"
            label="Resume"
            rules={[
              { required: true, message: 'Please upload your resume!' }
            ]}
          >
            <Upload
              beforeUpload={handleResumeUpload}
              showUploadList={false}
              accept=".pdf,.doc,.docx"
            >
              <Button 
                icon={<FileTextOutlined />}
                style={{ width: '100%' }}
                type={resumeFile ? 'primary' : 'default'}
              >
                {resumeFile ? `Resume: ${resumeFile.name}` : 'Upload Resume (PDF/DOC)'}
              </Button>
            </Upload>
          </Form.Item>

          <Form.Item
            name="linkedin_url"
            label="LinkedIn Profile (Optional)"
          >
            <Input 
              placeholder="https://linkedin.com/in/yourprofile"
            />
          </Form.Item>

          <Form.Item
            name="portfolio_url"
            label="Portfolio/Website (Optional)"
          >
            <Input 
              placeholder="https://yourportfolio.com"
            />
          </Form.Item>

          <Divider />

          <div style={{ textAlign: 'center' }}>
            <Space size="large">
              <Button 
                size="large"
                onClick={handleClose}
                style={{ minWidth: '120px' }}
              >
                Cancel
              </Button>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={loading}
                icon={<SendOutlined />}
                size="large"
                style={{ 
                  minWidth: '160px',
                  background: 'linear-gradient(45deg, #52c41a, #1890ff)',
                  border: 'none',
                  fontWeight: 'bold'
                }}
              >
                Submit Application
              </Button>
            </Space>
          </div>
        </Form>
      </div>
    </Modal>
  );
};

export default JobApplicationModal;
