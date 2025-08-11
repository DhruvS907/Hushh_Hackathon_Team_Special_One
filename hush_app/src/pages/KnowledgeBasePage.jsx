import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, ListGroup, Spinner, Form, Alert, Card } from 'react-bootstrap';
import { FiFileText, FiTrash2, FiUpload, FiArrowLeft, FiInbox } from 'react-icons/fi';
import axios from 'axios';
import UserContext from '../UserContext/userContext';
import '../styles/KnowledgeBasePage.css'; // New CSS file for styling

function KnowledgeBasePage() {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploading, setUploading] = useState(false);
  const [visible, setVisible] = useState(false);

  const { user } = useContext(UserContext);
  const navigate = useNavigate();

  useEffect(() => {
    // Trigger fade-in animation
    setTimeout(() => setVisible(true), 100);
    
    const fetchFiles = async () => {
      if (!user?.email) {
        setError("User information not found. Please log in again.");
        setLoading(false);
        return;
      }
      setLoading(true);
      setError('');
      try {
        const response = await axios.get(`http://localhost:8000/api/knowledge-base/files?user_email=${user.email}`);
        setFiles(response.data.files || []);
      } catch (err) {
        setError('Failed to fetch knowledge base files.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchFiles();
  }, [user]);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
    setError('');
    setSuccess('');
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      setError('Please select a file to upload.');
      return;
    }
    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('user_email', user.email);

    try {
      const response = await axios.post('http://localhost:8000/api/knowledge-base/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSuccess(response.data.message);
      // Refresh the list after a successful upload
      setFiles(prevFiles => [...prevFiles, selectedFile.name].sort());
      setSelectedFile(null);
      if(document.getElementById('kb-file-input')) {
        document.getElementById('kb-file-input').value = null;
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not upload file. It may already exist.');
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? This cannot be undone.`)) {
      return;
    }
    setError('');
    setSuccess('');
    try {
      await axios.delete(`http://localhost:8000/api/knowledge-base/files/${filename}?user_email=${user.email}`);
      setSuccess(`File "${filename}" deleted successfully.`);
      // Refresh the list after a successful delete
      setFiles(prevFiles => prevFiles.filter(f => f !== filename));
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not delete file.');
      console.error(err);
    }
  };

  return (
    <div className="kb-page-wrapper">
      <Button variant="link" className="back-button" onClick={() => navigate('/home')}>
        <FiArrowLeft /> Back to Home
      </Button>

      <div className={`kb-container ${visible ? 'visible' : ''}`}>
        <div className="kb-header">
          <h1 className="kb-brand-text">Knowledge Base</h1>
          <p className="kb-action-description">
            Manage the files your AI assistant uses to provide context and attachments.
          </p>
        </div>

        {error && <Alert variant="danger" className="mt-3">{error}</Alert>}
        {success && <Alert variant="success" className="mt-3">{success}</Alert>}

        {/* --- Upload Section --- */}
        <Card className="kb-card">
          <Card.Body>
            <Card.Title>Upload New Document</Card.Title>
            <Form onSubmit={handleUpload}>
              <Form.Group controlId="kb-file-input" className="mb-3">
                <Form.Control type="file" onChange={handleFileChange} accept=".txt,.md,.pdf" />
              </Form.Group>
              <Button variant="outline-light" type="submit" className="w-100 splash-btn" disabled={uploading || !selectedFile}>
                {uploading ? <Spinner as="span" animation="border" size="sm" /> : <FiUpload />}
                <span className="ms-2">{uploading ? 'Uploading...' : 'Upload File'}</span>
              </Button>
            </Form>
          </Card.Body>
        </Card>

        {/* --- File List Section --- */}
        <div className="file-list-container mt-4">
          <h5 className="kb-brand-text">Your Documents</h5>
          {loading ? (
            <div className="text-center p-5"><Spinner animation="border" variant="light" /></div>
          ) : (
            <ListGroup>
              {files.length > 0 ? files.map(file => (
                <ListGroup.Item key={file} className="kb-list-item">
                  <div className="file-info">
                    <FiFileText className="me-2" />
                    <span>{file}</span>
                  </div>
                  <Button variant="outline-danger" size="sm" onClick={() => handleDelete(file)}>
                    <FiTrash2 />
                  </Button>
                </ListGroup.Item>
              )) : (
                <div className="no-files-message">
                  <FiInbox size={40} />
                  <p className="mt-3">Your knowledge base is empty.</p>
                  <span>Upload a document to get started.</span>
                </div>
              )}
            </ListGroup>
          )}
        </div>
      </div>
    </div>
  );
}

export default KnowledgeBasePage;
