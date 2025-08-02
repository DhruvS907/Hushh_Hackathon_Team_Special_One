import React, { useEffect, useState, useContext } from "react";
import { Card, Badge, Spinner, Button, Modal, Form, Alert } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import { FiArrowLeft, FiMoreVertical, FiRefreshCcw, FiCheck, FiX, FiMessageSquare, FiUpload, FiPaperclip } from "react-icons/fi";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/SmartReply.css";
import axios from "axios";
import SidebarMenu from "../components/SlidebarMenu";
import UserContext from "../UserContext/userContext";

function SmartReply() {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [generatedResponse, setGeneratedResponse] = useState(null);
  const [showResponseModal, setShowResponseModal] = useState(false);
  const [userSuggestion, setUserSuggestion] = useState("");
  const [processingEmailId, setProcessingEmailId] = useState(null);
  const [regenerating, setRegenerating] = useState(false);
  const [actionLoading, setActionLoading] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [regenerationError, setRegenerationError] = useState(""); // For modal-specific errors

  const navigate = useNavigate();
  const { user } = useContext(UserContext);

  useEffect(() => {
    fetchEmails();
  }, []);

  const fetchEmails = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post("http://localhost:8000/api/summarize");
      if (res.data.emails && Array.isArray(res.data.emails)) {
        setEmails(res.data.emails);
      } else {
        setError("Unexpected backend response.");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch emails.");
    } finally {
      setLoading(false);
    }
  };

  const generateEmailId = (email) => {
    return String(Math.abs(hashCode(email.subject + email.sender)));
  };

  const hashCode = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash;
  };

  const handleGenerateReply = async (email) => {
    const emailId = generateEmailId(email);
    setProcessingEmailId(emailId);
    setSelectedEmail(email);
    
    // Reset modal state
    setUserSuggestion("");
    setSelectedFile(null);
    setRegenerationError("");

    if (!user?.consentToken) {
        setError("Consent token is missing. Please log in again to provide consent.");
        setProcessingEmailId(null);
        return;
    }

    try {
      const response = await axios.post("http://localhost:8000/api/process-email", {
        email_id: emailId,
        consent_token: user.consentToken, // Include consent token
        user_suggestion: null,
        gmail_message_id: email.id,
        gmail_thread_id: email.threadId,
        user_email: user?.email,
      });

      setGeneratedResponse(response.data);
      setShowResponseModal(true);
      setSuccessMessage("");
    } catch (err) {
      console.error("Error generating reply:", err);
      const errorMessage = err.response?.data?.detail || "Failed to generate reply. Please try again.";
      setError(errorMessage);
    } finally {
      setProcessingEmailId(null);
    }
  };

  const handleRegenerateReply = async () => {
    if (!generatedResponse?.response_id) return;
    
    setRegenerating(true);
    setRegenerationError(""); // Clear previous errors
    
    const formData = new FormData();
    formData.append("response_id", generatedResponse.response_id);
    formData.append("action", "regenerate");
    if (userSuggestion) {
      formData.append("user_suggestion", userSuggestion);
    }
    if (selectedFile) {
      formData.append("file", selectedFile);
    }

    try {
      const response = await axios.post("http://localhost:8000/api/response-action", formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setGeneratedResponse(prev => ({
        ...prev,
        ...response.data,
        generated_response: response.data.generated_response,
      }));

      setUserSuggestion("");
      setSelectedFile(null);
      setSuccessMessage("Response regenerated successfully!");
      
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      console.error("Error regenerating reply:", err);
      setRegenerationError("Failed to regenerate. Please try again.");
    } finally {
      setRegenerating(false);
    }
  };

  const handleResponseAction = async (action) => {
    if (!generatedResponse) return;
    
    setActionLoading(action);
    const formData = new FormData();
    formData.append("response_id", generatedResponse.response_id);
    formData.append("action", action);

    try {
      await axios.post("http://localhost:8000/api/response-action", formData);

      if (action === "approve") {
        setSuccessMessage("Email sent successfully! ✉️");
        setShowResponseModal(false);
        setEmails(prev => prev.filter(email => generateEmailId(email) !== generateEmailId(selectedEmail)));
      } else if (action === "reject") {
        setSuccessMessage("Email response rejected. No email will be sent.");
        setShowResponseModal(false);
      }
      setTimeout(() => setSuccessMessage(""), 4000);
    } catch (err) {
      console.error(`Error ${action}ing response:`, err);
      setError(`Failed to ${action} response. Please try again.`);
    } finally {
      setActionLoading("");
    }
  };

  const getPriorityVariant = (level) => {
    switch (level) {
      case "High": return "danger";
      case "Medium": return "warning";
      case "Low": return "secondary";
      default: return "info";
    }
  };

  const getAgentTypeColor = (agentType) => {
    switch (agentType) {
      case "scheduler": return "primary";
      case "info_responder": return "info";
      case "general_responder": return "secondary";
      case "no_response": return "dark";
      default: return "light";
    }
  };

  const shouldShowReplyButton = (intent) => {
    const noReplyIntents = [
      "Marketing emails or newsletters",
      "Informational only – no action required (FYI)",
      "Announcing a new product or feature",
      "Shipping, delivery, or order tracking update"
    ];
    return !noReplyIntents.includes(intent);
  };

  return (
    <div className="smart-reply-wrapper">
      <div className="top-navbar">
        <FiArrowLeft className="nav-icon" onClick={() => navigate("/home")} title="Back" />
        <h3 className="nav-title">Smart Email Replies</h3>
        <FiMoreVertical className="nav-icon" onClick={() => setSidebarOpen(!sidebarOpen)} title="Menu" />
      </div>
      <SidebarMenu isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {successMessage && <Alert variant="success" className="success-alert">{successMessage}</Alert>}
      <div className="email-list">
        {loading && <div className="loading-spinner"><Spinner animation="border" /><p>Loading your emails...</p></div>}
        {error && <div className="error-message">{error}</div>}
        {!loading && emails.length === 0 && <div className="no-emails"><FiMessageSquare size={48} className="mb-3" /><h5>No emails to reply to!</h5><p>All caught up with your inbox.</p></div>}
        {!loading && emails.map((email) => {
          const emailId = generateEmailId(email);
          const isProcessing = processingEmailId === emailId;
          return (
            <Card key={emailId} className="email-card-smart">
              <Card.Body>
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div>
                    <h5 className="email-subject">{email.subject || "No Subject"}</h5>
                    <p className="email-from">From: {email.sender}</p>
                  </div>
                  <Badge bg={getPriorityVariant(email.priority)} className="priority-badge">{email.priority || "Medium"}</Badge>
                </div>
                <p className="email-summary">{email.summary || "No summary available."}</p>
                <div className="d-flex justify-content-between align-items-center">
                  <Badge bg="info" className="intent-badge">{email.intent || "Unknown"}</Badge>
                  {shouldShowReplyButton(email.intent) ? (
                    <Button variant="primary" size="sm" onClick={() => handleGenerateReply(email)} disabled={isProcessing} className="generate-reply-btn">
                      {isProcessing ? <><Spinner animation="border" size="sm" className="me-2" />Generating...</> : <><FiMessageSquare className="me-2" />Generate Reply</>}
                    </Button>
                  ) : <Badge bg="secondary">No Reply Needed</Badge>}
                </div>
              </Card.Body>
            </Card>
          );
        })}
      </div>

      <Modal show={showResponseModal} onHide={() => { setShowResponseModal(false); setRegenerationError(""); }} size="lg">
        <Modal.Header closeButton className="modal-header-dark"><Modal.Title>Generated Email Response</Modal.Title></Modal.Header>
        <Modal.Body className="modal-body-dark">
          <Alert variant="danger" show={!!regenerationError}>{regenerationError}</Alert>
          {selectedEmail && (
            <div className="original-email-info mb-3">
              <h6>Replying to:</h6>
              <div className="bg-dark p-2 rounded">
                <strong>Subject:</strong> {selectedEmail.subject}<br />
                <strong>From:</strong> {selectedEmail.sender}<br />
                <strong>Summary:</strong> {selectedEmail.summary}
              </div>
            </div>
          )}

          {generatedResponse && (
            <>
              <div className="response-info mb-3">
                <Badge bg={getAgentTypeColor(generatedResponse.generated_response?.response_type)} className="me-2">Agent: {generatedResponse.generated_response?.response_type || "Unknown"}</Badge>
                <Badge bg="success">Confidence: {Math.round((generatedResponse.generated_response?.confidence || 0) * 100)}%</Badge>
              </div>
              <div className="generated-response-content">
                <h6>Generated Response:</h6>
                <div className="response-text">{generatedResponse.generated_response?.message || "No response generated"}</div>
              </div>
              {generatedResponse.generated_response?.reasoning && (
                <div className="reasoning mt-3">
                  <h6>AI Reasoning:</h6>
                  <small className="text-white">{generatedResponse.generated_response.reasoning}</small>
                </div>
              )}
            </>
          )}

          <div className="user-suggestion-section mt-4">
            <Form.Group>
              <Form.Label>Add your suggestions (optional):</Form.Label>
              <Form.Control as="textarea" rows={2} value={userSuggestion} onChange={(e) => setUserSuggestion(e.target.value)} placeholder="e.g., Make it more formal..."/>
            </Form.Group>
            <Form.Group className="mt-3">
              <Form.Label>Attach document for context (optional):</Form.Label>
              <div className="file-upload-wrapper">
                <Button as="label" htmlFor="file-upload" variant="outline-secondary" className="file-upload-btn">
                  <FiUpload className="me-2" />
                  Choose File
                </Button>
                <Form.Control id="file-upload" type="file" onChange={(e) => setSelectedFile(e.target.files[0])} style={{ display: 'none' }} />
                {selectedFile && (
                  <div className="file-name-display">
                    <FiPaperclip size={14} className="me-1" />
                    <span>{selectedFile.name}</span>
                    <Button variant="link" size="sm" onClick={() => setSelectedFile(null)} className="file-clear-btn"><FiX /></Button>
                  </div>
                )}
              </div>
            </Form.Group>
          </div>
        </Modal.Body>
        <Modal.Footer className="modal-footer-dark">
          <Button variant="outline-warning" onClick={handleRegenerateReply} disabled={regenerating || actionLoading}>
            {regenerating ? <><Spinner animation="border" size="sm" className="me-2" />Regenerating...</> : <><FiRefreshCcw className="me-2" />Regenerate</>}
          </Button>
          <Button variant="outline-danger" onClick={() => handleResponseAction("reject")} disabled={actionLoading === "reject" || regenerating}>
            {actionLoading === "reject" ? <Spinner animation="border" size="sm" /> : <><FiX className="me-2" />Reject</>}
          </Button>
          <Button variant="success" onClick={() => handleResponseAction("approve")} disabled={actionLoading === "approve" || regenerating}>
            {actionLoading === "approve" ? <><Spinner animation="border" size="sm" className="me-2" />Sending...</> : <><FiCheck className="me-2" />Approve & Send</>}
          </Button>
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default SmartReply;