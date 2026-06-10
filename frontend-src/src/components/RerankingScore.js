import React, { useState } from 'react';
import { 
  Card, 
  Progress, 
  Tooltip, 
  Button, 
  Modal, 
  Typography, 
  Row, 
  Col, 
  Tag,
  Space,
  Divider,
  Alert
} from 'antd';
import { 
  TrophyOutlined, 
  InfoCircleOutlined, 
  StarOutlined,
  BulbOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';

const { Text, Title, Paragraph } = Typography;

const RerankingScore = ({ 
  score, 
  explanations = null, 
  showDetails = false,
  jobId = null,
  onGetExplanation = null,
  compact = false
}) => {
  const [explanationModalVisible, setExplanationModalVisible] = useState(false);
  const [explanationData, setExplanationData] = useState(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#52c41a'; // Green - Excellent
    if (score >= 0.6) return '#1890ff'; // Blue - Good
    if (score >= 0.4) return '#faad14'; // Orange - Fair
    return '#ff4d4f'; // Red - Poor
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return 'Excellent Match';
    if (score >= 0.6) return 'Good Match';
    if (score >= 0.4) return 'Fair Match';
    return 'Poor Match';
  };

  const getScoreIcon = (score) => {
    if (score >= 0.8) return <TrophyOutlined style={{ color: '#52c41a' }} />;
    if (score >= 0.6) return <StarOutlined style={{ color: '#1890ff' }} />;
    return <InfoCircleOutlined style={{ color: '#faad14' }} />;
  };

  const handleGetExplanation = async () => {
    if (!onGetExplanation || !jobId) return;
    
    setLoadingExplanation(true);
    try {
      const explanation = await onGetExplanation(jobId);
      setExplanationData(explanation);
      setExplanationModalVisible(true);
    } catch (error) {
      console.error('Failed to get explanation:', error);
    } finally {
      setLoadingExplanation(false);
    }
  };

  const getFactorIcon = (factor) => {
    const icons = {
      skill_match: '🎯',
      experience_match: '📈',
      location_preference: '📍',
      salary_expectation: '💰',
      semantic_similarity: '🔍',
      company_preference: '🏢'
    };
    return icons[factor] || '📊';
  };

  const formatFactorName = (factor) => {
    const names = {
      skill_match: 'Skills Match',
      experience_match: 'Experience Level',
      location_preference: 'Location',
      salary_expectation: 'Salary',
      semantic_similarity: 'Job Description Fit',
      company_preference: 'Company & Benefits'
    };
    return names[factor] || factor.replace(/_/g, ' ');
  };

  const renderExplanationModal = () => (
    <Modal
      title={
        <Space>
          <BulbOutlined />
          <span>Why This Job Was Recommended</span>
        </Space>
      }
      open={explanationModalVisible}
      onCancel={() => setExplanationModalVisible(false)}
      footer={null}
      width={900}
    >
      {explanationData && (
        <div>
          {/* Job Overview Card */}
          <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
            <Row gutter={16}>
              <Col span={12}>
                <Text strong>Job Title:</Text>
                <br />
                <Text style={{ fontSize: '16px' }}>{explanationData.job_title}</Text>
              </Col>
              <Col span={12}>
                <Text strong>Company:</Text>
                <br />
                <Text style={{ fontSize: '16px' }}>{explanationData.company}</Text>
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            <Row gutter={16}>
              <Col span={8}>
                <Text strong>Overall Match Score:</Text>
                <br />
                <Progress 
                  percent={Math.round(explanationData.final_score * 100)} 
                  strokeColor={getScoreColor(explanationData.final_score)}
                  format={() => `${(explanationData.final_score * 100).toFixed(1)}%`}
                />
              </Col>
              <Col span={8}>
                <Text strong>Match Quality:</Text>
                <br />
                <Tag color={getScoreColor(explanationData.final_score)} style={{ marginTop: 4 }}>
                  {getScoreLabel(explanationData.final_score)}
                </Tag>
              </Col>
              <Col span={8}>
                <Text strong>Analysis Method:</Text>
                <br />
                <Tag 
                  color={explanationData.scoring_method?.includes('AI') ? 'purple' : 'default'} 
                  style={{ marginTop: 4 }}
                >
                  {explanationData.scoring_method?.includes('AI') ? '🤖 ' : '📊 '}
                  {explanationData.scoring_method || 'Standard Analysis'}
                </Tag>
              </Col>
            </Row>
          </Card>

          {/* Knowledge Graph Explanation */}
          {explanationData.knowledge_graph_explanation && (
            <Alert
              message={
                <Space>
                  <NodeIndexOutlined />
                  <Text strong>Knowledge Graph Insight</Text>
                </Space>
              }
              description={explanationData.knowledge_graph_explanation}
              type="info"
              showIcon={false}
              style={{ marginBottom: 16 }}
            />
          )}

          {/* Top Feature Attributions */}
          {explanationData.top_feature_attributions && explanationData.top_feature_attributions.length > 0 && (
            <Card 
              size="small" 
              style={{ marginBottom: 16, borderColor: '#1890ff' }}
              title={
                <Space>
                  <ThunderboltOutlined style={{ color: '#1890ff' }} />
                  <Text strong>Key Matching Factors</Text>
                </Space>
              }
            >
              <Space wrap>
                {explanationData.top_feature_attributions.map((attr, idx) => (
                  <Tag key={idx} color="blue" style={{ padding: '4px 12px' }}>
                    {attr}
                  </Tag>
                ))}
              </Space>
            </Card>
          )}

          <Title level={5}>Detailed Ranking Factors</Title>
          {explanationData.factor_scores && Object.entries(explanationData.factor_scores).map(([factor, data]) => (
            <Card 
              key={factor} 
              size="small" 
              style={{ 
                marginBottom: 12,
                borderLeft: `4px solid ${getScoreColor(data.score)}`
              }}
            >
              <Row gutter={16} align="top">
                <Col span={8}>
                  <Space>
                    <span style={{ fontSize: '18px' }}>{getFactorIcon(factor)}</span>
                    <div>
                      <Text strong style={{ fontSize: '14px' }}>
                        {formatFactorName(factor)}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        Weight: {(data.weight * 100).toFixed(0)}% | 
                        Contribution: {(data.contribution * 100).toFixed(1)}%
                      </Text>
                    </div>
                  </Space>
                </Col>
                <Col span={6}>
                  <Progress 
                    percent={Math.round(data.score * 100)} 
                    strokeColor={getScoreColor(data.score)}
                    size="small"
                    format={() => `${(data.score * 100).toFixed(0)}%`}
                  />
                </Col>
                <Col span={10}>
                  <Paragraph 
                    style={{ 
                      margin: 0, 
                      fontSize: '13px',
                      color: '#595959',
                      background: '#f5f5f5',
                      padding: '8px 12px',
                      borderRadius: '4px'
                    }}
                  >
                    {data.explanation}
                  </Paragraph>
                </Col>
              </Row>
            </Card>
          ))}
        </div>
      )}
    </Modal>
  );

  if (!score && score !== 0) return null;

  // Compact view for job cards - badge style with info button
  if (compact) {
    return (
      <>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div 
            style={{ 
              backgroundColor: getScoreColor(score),
              borderRadius: '12px',
              padding: '8px 12px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              minWidth: '60px',
              cursor: 'pointer'
            }}
            onClick={handleGetExplanation}
          >
            <div style={{ 
              color: '#fff', 
              fontWeight: 'bold', 
              fontSize: '18px',
              lineHeight: '1.2'
            }}>
              {Math.round(score * 100)}%
            </div>
            <div style={{ 
              color: '#fff', 
              fontSize: '11px',
              opacity: 0.9
            }}>
              Match
            </div>
          </div>
          <Tooltip title="Why this match? Click for details">
            <Button 
              type="text" 
              size="small" 
              icon={<InfoCircleOutlined style={{ color: '#1890ff', fontSize: '18px' }} />}
              onClick={handleGetExplanation}
              loading={loadingExplanation}
              style={{ padding: '4px' }}
            />
          </Tooltip>
        </div>
        {renderExplanationModal()}
      </>
    );
  }

  // Full view for recommendation pages
  return (
    <>
      <Card 
        size="small" 
        style={{ 
          marginTop: 8,
          border: `1px solid ${getScoreColor(score)}`,
          backgroundColor: `${getScoreColor(score)}08`
        }}
      >
        <Row gutter={8} align="middle">
          <Col flex="auto">
            <Space size="small">
              {getScoreIcon(score)}
              <Text strong style={{ color: getScoreColor(score) }}>
                Match Score: {(score * 100).toFixed(1)}%
              </Text>
              <Tag color={getScoreColor(score)} size="small">
                {getScoreLabel(score)}
              </Tag>
            </Space>
          </Col>
          <Col>
            <Progress 
              percent={Math.round(score * 100)} 
              strokeColor={getScoreColor(score)}
              size="small"
              style={{ width: 100 }}
              showInfo={false}
            />
          </Col>
          {(showDetails || onGetExplanation) && (
            <Col>
              <Tooltip title="Get detailed explanation">
                <Button 
                  type="text" 
                  size="small" 
                  icon={<InfoCircleOutlined />}
                  onClick={handleGetExplanation}
                  loading={loadingExplanation}
                />
              </Tooltip>
            </Col>
          )}
        </Row>
      </Card>
      
      {renderExplanationModal()}
    </>
  );
};

export default RerankingScore;
