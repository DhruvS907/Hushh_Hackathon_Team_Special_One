import React, { useEffect, useState, useContext } from "react";
import { Card, Badge, Spinner, Button, Modal, Form, Alert, Tab, Tabs } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import { FiArrowLeft, FiMoreVertical, FiRefreshCcw, FiCheck, FiX, FiClock, FiCheckCircle, FiUpload, FiPaperclip } from "react-icons/fi";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/PendingResponses.css";
import "../styles/SmartReply.css"; // Re-using some styles for the file upload
import axios from "axios";
import SidebarMenu from "../components/SlidebarMenu";
import UserContext from "../UserContext/userContext";

function PendingResponses() {
  const [pendingResponses, setPendingResponses] = useState([]);
  const [responseHistory, setResponseHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedResponse, setSelectedResponse] = useState(null);
  const [showResponseModal, setShowResponseModal] = useState(false);
  const [userSuggestion, setUserSuggestion] = useState("");
  const [actionLoading, setActionLoading] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [activeTab, setActiveTab] = useState("pending");
  const [selectedFile, setSelectedFile] = useState(null);
  const [regenerationError, setRegenerationError] = useState("");

  const navigate = useNavigate();
  const { user } = useContext(UserContext);

  useEffect(() => {
    if (activeTab === "pending") {
      fetchPendingResponses();
    } else {
      fetchResponseHistory();
    }
  }, [activeTab, user]); // Refetch when user changes

  const fetchPendingResponses = async () => {
    setLoading(true);
    setError(null);
    try {
      const userEmail = user?.email || "user@example.com";
      const res = await axios.get(`http://localhost:8000/api/pending-responses?user_email=${userEmail}`);
      setPendingResponses(res.data.pending_responses || []);
    } catch (err) {
      console.error("Error fetching pending responses:", err);
      setError("Failed to fetch pending responses.");
    } finally {
      setLoading(false);
    }
  };

  const fetchResponseHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const userEmail = user?.email || "user@example.com";
      const res = await axios.get(`http://localhost:8000/api/response-history?user_email=${userEmail}`);
      setResponseHistory(res.data.response_history || []);
    } catch (err) {
      console.error("Error fetching response history:", err);
      setError("Failed to fetch response history.");
    } finally {
      setLoading(false);
    }
  };

  const handleViewResponse = (response) => {
    setSelectedResponse(response);
    setUserSuggestion(response.user_suggestion || "");
    setSelectedFile(null);
    setRegenerationError("");
    setShowResponseModal(true);
  };

  const handleRegenerateResponse = async () => {
    if (!selectedResponse) return;
    
    setActionLoading("regenerate");
    setRegenerationError("");

    const formData = new FormData();
    formData.append("response_id", selectedResponse.id);
    formData.append("action", "regenerate");
    if (userSuggestion) {
      formData.append("user_suggestion", userSuggestion);
    }
    if (selectedFile) {
      formData.append("file", selectedFile);
    }

    try {
      const response = await axios.post("http://localhost:8000/api/response-action", formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSelectedResponse({
        ...selectedResponse,
        generated_response: response.data.generated_response.message,
        agent_type: response.data.generated_response.response_type,
        user_suggestion: userSuggestion
      });

      setSuccessMessage("Response regenerated successfully!");
      setSelectedFile(null);
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (err) {
      console.error("Error regenerating response:", err);
      setRegenerationError("Failed to regenerate response. Please try again.");
    } finally {
      setActionLoading("");
    }
  };

  const handleResponseAction = async (action) => {
    if (!selectedResponse) return;
    
    setActionLoading(action);
    const formData = new FormData();
    formData.append("response_id", selectedResponse.id);
    formData.append("action", action);

    try {
      await axios.post("http://localhost:8000/api/response-action", formData);

      if (action === "approve") {
        setSuccessMessage("Email sent successfully! ✉️");
        setShowResponseModal(false);
        setPendingResponses(prev => prev.filter(r => r.id !== selectedResponse.id));
        fetchResponseHistory();
        setActiveTab("history");
      } else if (action === "reject") {
        setSuccessMessage("Email response rejected. No email will be sent.");
        setShowResponseModal(false);
        setPendingResponses(prev => prev.filter(r => r.id !== selectedResponse.id));
      }

      setTimeout(() => setSuccessMessage(""), 4000);
    } catch (err) {
      console.error(`Error ${action}ing response:`, err);
      setError(`Failed to ${action} response. Please try again.`);
    } finally {
      setActionLoading("");
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

  const getStatusColor = (status) => {
    switch (status) {
      case "approved": return "success";
      case "rejected": return "danger";
      case "pending": return "warning";
      default: return "secondary";
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const renderResponseCard = (response, isPending = true) => (
    <Card key={response.id} className="response-card">
      <Card.Body>
        <div className="d-flex justify-content-between align-items-start mb-2">
          <div className="flex-grow-1">
            <h5 className="response-subject">{response.email_subject}</h5>
            <p className="response-sender">From: {response.sender_email}</p>
            <p className="response-date">Created: {formatDate(response.created_at)}</p>
          </div>
          <div className="d-flex flex-column align-items-end gap-2">
            <Badge bg={getAgentTypeColor(response.agent_type)}>{response.agent_type}</Badge>
            {!isPending && <Badge bg={getStatusColor(response.status)}>{response.status}</Badge>}
          </div>
        </div>
        <p className="response-summary">{response.email_summary}</p>
        <div className="d-flex justify-content-between align-items-center">
          <Badge bg="info" className="intent-badge">{response.email_intent}</Badge>
          <Button variant="outline-primary" size="sm" onClick={() => handleViewResponse(response)} className="view-response-btn">View Response</Button>
        </div>
      </Card.Body>
    </Card>
  );

  return (
    <div className="pending-responses-wrapper">
      <div className="top-navbar">
        <FiArrowLeft className="nav-icon" onClick={() => navigate("/home")} title="Back" />
        <h3 className="nav-title">Email Responses</h3>
        <FiMoreVertical className="nav-icon" onClick={() => setSidebarOpen(!sidebarOpen)} title="Menu" />
      </div>
      <SidebarMenu isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {successMessage && <Alert variant="success" className="success-alert">{successMessage}</Alert>}
      <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)} className="response-tabs mb-4">
        <Tab eventKey="pending" title={<span><FiClock className="me-2" />Pending ({pendingResponses.length})</span>}>
          <div className="responses-list">
            {loading && <div className="loading-spinner"><Spinner animation="border" /><p>Loading pending responses...</p></div>}
            {error && <div className="error-message">{error}</div>}
            {!loading && pendingResponses.length === 0 && <div className="no-responses"><FiClock size={48} className="mb-3" /><h5>No pending responses!</h5><p>All your email responses have been handled.</p></div>}
            {!loading && pendingResponses.map(response => renderResponseCard(response, true))}
          </div>
        </Tab>
        <Tab eventKey="history" title={<span><FiCheckCircle className="me-2" />History ({responseHistory.length})</span>}>
          <div className="responses-list">
            {loading && <div className="loading-spinner"><Spinner animation="border" /><p>Loading response history...</p></div>}
            {error && <div className="error-message">{error}</div>}
            {!loading && responseHistory.length === 0 && <div className="no-responses"><FiCheckCircle size={48} className="mb-3" /><h5>No response history!</h5><p>Your handled responses will appear here.</p></div>}
            {!loading && responseHistory.map(response => renderResponseCard(response, false))}
          </div>
        </Tab>
      </Tabs>

      <Modal show={showResponseModal} onHide={() => { setShowResponseModal(false); setRegenerationError(""); }} size="lg">
        <Modal.Header closeButton className="modal-header-dark"><Modal.Title>Email Response Details</Modal.Title></Modal.Header>
        <Modal.Body className="modal-body-dark">
          <Alert variant="danger" show={!!regenerationError}>{regenerationError}</Alert>
          {selectedResponse && (
            <>
              <div className="original-email-info mb-3">
                <h6>Original Email:</h6>
                <div className="bg-dark p-2 rounded">
                  <strong>Subject:</strong> {selectedResponse.email_subject}<br />
                  <strong>From:</strong> {selectedResponse.sender_email}<br />
                  <strong>Summary:</strong> {selectedResponse.email_summary}<br />
                  <strong>Intent:</strong> {selectedResponse.email_intent}
                </div>
              </div>
              <div className="response-info mb-3">
                <Badge bg={getAgentTypeColor(selectedResponse.agent_type)} className="me-2">Agent: {selectedResponse.agent_type}</Badge>
                <Badge bg={getStatusColor(selectedResponse.status)}>Status: {selectedResponse.status}</Badge>
              </div>
              <div className="generated-response-content">
                <h6>Generated Response:</h6>
                <div className="response-text">{selectedResponse.generated_response}</div>
              </div>
              {selectedResponse.user_suggestion && (
                <div className="user-suggestion-display mt-3">
                  <h6>Previous Suggestion:</h6>
                  <div className="suggestion-text">{selectedResponse.user_suggestion}</div>
                </div>
              )}
              {selectedResponse.status === "pending" && (
                <div className="user-suggestion-section mt-4">
                  <Form.Group>
                    <Form.Label>Add your suggestions (optional):</Form.Label>
                    <Form.Control as="textarea" rows={2} value={userSuggestion} onChange={(e) => setUserSuggestion(e.target.value)} placeholder="e.g., Make it more formal..."/>
                  </Form.Group>
                  <Form.Group className="mt-3">
                    <Form.Label>Attach document for context (optional):</Form.Label>
                    <div className="file-upload-wrapper">
                      <Button as="label" htmlFor="file-upload-pending" variant="outline-secondary" className="file-upload-btn">
                        <FiUpload className="me-2" />
                        Choose File
                      </Button>
                      <Form.Control id="file-upload-pending" type="file" onChange={(e) => setSelectedFile(e.target.files[0])} style={{ display: 'none' }} />
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
              )}
            </>
          )}
        </Modal.Body>
        <Modal.Footer className="modal-footer-dark">
          {selectedResponse?.status === "pending" && (
            <>
              <Button variant="outline-warning" onClick={handleRegenerateResponse} disabled={actionLoading === "regenerate"}>
                {actionLoading === "regenerate" ? <><Spinner animation="border" size="sm" className="me-2" />Regenerating...</> : <><FiRefreshCcw className="me-2" />Regenerate</>}
              </Button>
              <Button variant="outline-danger" onClick={() => handleResponseAction("reject")} disabled={actionLoading === "reject" || actionLoading === "regenerate"}>
                {actionLoading === "reject" ? <Spinner animation="border" size="sm" /> : <><FiX className="me-2" />Reject</>}
              </Button>
              <Button variant="success" onClick={() => handleResponseAction("approve")} disabled={actionLoading === "approve" || actionLoading === "regenerate"}>
                {actionLoading === "approve" ? <><Spinner animation="border" size="sm" className="me-2" />Sending...</> : <><FiCheck className="me-2" />Approve & Send</>}
              </Button>
            </>
          )}
          {selectedResponse?.status !== "pending" && <Button variant="secondary" onClick={() => setShowResponseModal(false)}>Close</Button>}
        </Modal.Footer>
      </Modal>
    </div>
  );
}

export default PendingResponses;
