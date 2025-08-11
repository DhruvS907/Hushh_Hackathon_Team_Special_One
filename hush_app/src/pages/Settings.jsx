// src/pages/Settings.jsx
import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Button, Card, Container, Row, Col, Alert, Spinner } from 'react-bootstrap';
import { FiUser, FiSave, FiLogOut, FiArrowLeft } from 'react-icons/fi';
import axios from 'axios';
import UserContext from '../UserContext/userContext';
import '../styles/Settings.css'; // We will create this CSS file next

function Settings() {
  const navigate = useNavigate();
  const { user, setUser } = useContext(UserContext);
  
  const [formData, setFormData] = useState({
    name: '',
    linkedin: '',
    github: '',
  });
  
  const [tokenExpiry, setTokenExpiry] = useState(24); // Default to 24 hours
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Fetch user data when the component loads
  useEffect(() => {
    if (user?.email) {
      setLoading(true);
      axios.get(`http://localhost:8000/api/user-details?user_email=${user.email}`)
        .then(response => {
          setFormData({
            name: response.data.name || '',
            linkedin: response.data.linkedin || '',
            github: response.data.github || '',
          });
          // Also, get the stored token expiry if available
          const storedExpiry = localStorage.getItem('tokenExpiryHours');
          if (storedExpiry) {
            setTokenExpiry(parseInt(storedExpiry, 10));
          }
        })
        .catch(err => {
          setError('Failed to fetch user details.');
          console.error(err);
        })
        .finally(() => setLoading(false));
    }
  }, [user]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleUpdateDetails = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const payload = { ...formData, gmail: user.email };
      const response = await axios.post('http://localhost:8000/api/update-settings', payload);
      setSuccess(response.data.message);
      // Update user context with new name
      setUser(prevUser => ({...prevUser, name: formData.name}));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update details.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  const handleTokenExpiryChange = (e) => {
      const hours = parseInt(e.target.value, 10);
      setTokenExpiry(hours);
      // Store in localStorage so it can be used during the next login
      localStorage.setItem('tokenExpiryHours', hours);
      setSuccess(`Token expiry updated to ${hours} hours. This will apply on your next login.`);
  };

  const handleLogout = () => {
    // Clear user context and any stored tokens/data
    setUser(null);
    sessionStorage.removeItem('kbConsentToken');
    localStorage.removeItem('tokenExpiryHours');
    // Navigate to the root/login page
    navigate('/');
  };

  return (
    <div className="settings-wrapper">
      <Container>
        <Row className="justify-content-center">
          <Col md={8} lg={6}>
            <div className="top-navbar-settings">
              <FiArrowLeft className="nav-icon" onClick={() => navigate("/home")} title="Back" />
              <h3 className="nav-title">Settings</h3>
            </div>
            
            {error && <Alert variant="danger">{error}</Alert>}
            {success && <Alert variant="success">{success}</Alert>}

            <Card className="settings-card">
              <Card.Body>
                <Card.Title><FiUser className="me-2" />Profile Information</Card.Title>
                <Form onSubmit={handleUpdateDetails}>
                  <Form.Group className="mb-3" controlId="formName">
                    <Form.Label>Name</Form.Label>
                    <Form.Control
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="Enter your full name"
                      required
                    />
                  </Form.Group>
                  <Form.Group className="mb-3" controlId="formLinkedin">
                    <Form.Label>LinkedIn Profile URL</Form.Label>
                    <Form.Control
                      type="url"
                      name="linkedin"
                      value={formData.linkedin}
                      onChange={handleChange}
                      placeholder="https://linkedin.com/in/yourprofile"
                    />
                  </Form.Group>
                  <Form.Group className="mb-4" controlId="formGithub">
                    <Form.Label>GitHub Profile URL</Form.Label>
                    <Form.Control
                      type="url"
                      name="github"
                      value={formData.github}
                      onChange={handleChange}
                      placeholder="https://github.com/yourusername"
                    />
                  </Form.Group>
                  <Button variant="primary" type="submit" className="w-100" disabled={loading}>
                    <FiSave className="me-2" />
                    {loading ? <Spinner as="span" animation="border" size="sm" /> : 'Save Profile Changes'}
                  </Button>
                </Form>
              </Card.Body>
            </Card>

            <Card className="settings-card mt-4">
                <Card.Body>
                    <Card.Title>Token Settings</Card.Title>
                    <Form.Group controlId="formTokenExpiry">
                        <Form.Label>Login Token Expiry (in hours)</Form.Label>
                        <Form.Select value={tokenExpiry} onChange={handleTokenExpiryChange}>
                            <option value={1}>1 Hour</option>
                            <option value={8}>8 Hours</option>
                            <option value={24}>24 Hours (Default)</option>
                            <option value={168}>7 Days</option>
                        </Form.Select>
                        <Form.Text className="text-muted">
                            This setting will take effect the next time you log in.
                        </Form.Text>
                    </Form.Group>
                </Card.Body>
            </Card>

            <Card className="settings-card mt-4">
              <Card.Body>
                <Button variant="outline-danger" className="w-100" onClick={handleLogout}>
                  <FiLogOut className="me-2" />
                  Logout
                </Button>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
}

export default Settings;
