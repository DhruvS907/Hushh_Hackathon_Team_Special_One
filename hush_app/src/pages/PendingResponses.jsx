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
    if (!user?.email) return; // Don't fetch if user is not logged in

    if (activeTab === "pending") {
      fetchPendingResponses();
    } else {
      fetchResponseHistory();
    }
  }, [activeTab, user]);

  const fetchPendingResponses = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.get(`http://localhost:8000/api/pending-responses?user_email=${user.email}`);
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
      const res = await axios.get(`http://localhost:8000/api/response-history?user_email=${user.email}`);
      setResponseHistory(res.data.history || []);
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
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      // CHANGE: This is the critical fix.
      // The backend now returns the full updated response object.
      const updatedResponseData = response.data.generated_response;

      // Create the fully updated response object for our state
      const newResponseState = {
          ...selectedResponse,
          generated_response: updatedResponseData.message,
          agent_type: updatedResponseData.response_type,
          user_suggestion: userSuggestion // Reflect the latest suggestion
      };

      // 1. Update the state for the currently open modal
      setSelectedResponse(newResponseState);

      // 2. Update the main list of pending responses so the change is reflected when the modal closes
      setPendingResponses(prevList => prevList.map(item => 
        item.id === selectedResponse.id ? newResponseState : item
      ));

      setSuccessMessage("Response regenerated successfully!");
      setSelectedFile(null); // Clear the file input after regeneration
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

      setShowResponseModal(false);
      // Optimistically remove from the pending list
      setPendingResponses(prev => prev.filter(r => r.id !== selectedResponse.id));

      if (action === "approve") {
        setSuccessMessage("Email sent successfully! ✉️");
        // Optimistically add to the history list
        const approvedItem = { ...selectedResponse, status: 'approved' };
        setResponseHistory(prev => [approvedItem, ...prev]);

      } else if (action === "reject") {
        setSuccessMessage("Email response rejected.");
         // Optimistically add to the history list
        const rejectedItem = { ...selectedResponse, status: 'rejected' };
        setResponseHistory(prev => [rejectedItem, ...prev]);
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
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
  };

  const renderResponseCard = (response, isPending = true) => (
    <Card key={response.id} className="response-card">
      <Card.Body>
        <div className="d-flex justify-content-between align-items-start mb-2">
          <div className="flex-grow-1">
            <h5 className="response-subject">{response.email_subject}</h5>
            <p className="response-sender">To: {response.sender_email}</p>
            <p className="response-date">Created: {formatDate(response.created_at)}</p>
          </div>
          <div className="d-flex flex-column align-items-end gap-2">
            <Badge bg={getAgentTypeColor(response.agent_type)} className="type-badge">{response.agent_type?.replace('_', ' ')}</Badge>
            {!isPending && <Badge bg={getStatusColor(response.status)} className="status-badge">{response.status}</Badge>}
          </div>
        </div>
        <p className="response-summary">{response.email_summary}</p>
        <div className="d-flex justify-content-end align-items-center">
          <Button variant="outline-primary" size="sm" onClick={() => handleViewResponse(response)} className="view-response-btn">
            {isPending ? "Review & Action" : "View Details"}
          </Button>
        </div>
      </Card.Body>
    </Card>
  );

  return (
    <div className="pending-responses-wrapper">
      <div className="top-navbar">
        <FiArrowLeft className="nav-icon" onClick={() => navigate("/home")} title="Back" />
        <h3 className="nav-title">Manage Responses</h3>
        <FiMoreVertical className="nav-icon" onClick={() => setSidebarOpen(!sidebarOpen)} title="Menu" />
      </div>
      <SidebarMenu isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {successMessage && <Alert variant="success" className="success-alert">{successMessage}</Alert>}
      
      <div className="tabs-container">
        <Tabs activeKey={activeTab} onSelect={(k) => setActiveTab(k)} className="response-tabs mb-4">
          <Tab eventKey="pending" title={<><FiClock className="me-2" />Pending ({pendingResponses.length})</>}>
            <div className="responses-list">
              {loading && <div className="loading-spinner"><Spinner animation="border" /><p>Loading pending responses...</p></div>}
              {error && <div className="error-message">{error}</div>}
              {!loading && pendingResponses.length === 0 && <div className="no-responses"><FiClock size={48} className="mb-3" /><h5>No pending responses!</h5><p>All your email responses have been handled.</p></div>}
              {!loading && pendingResponses.map(response => renderResponseCard(response, true))}
            </div>
          </Tab>
          <Tab eventKey="history" title={<><FiCheckCircle className="me-2" />History ({responseHistory.length})</>}>
            <div className="responses-list">
              {loading && <div className="loading-spinner"><Spinner animation="border" /><p>Loading response history...</p></div>}
              {error && <div className="error-message">{error}</div>}
              {!loading && responseHistory.length === 0 && <div className="no-responses"><FiCheckCircle size={48} className="mb-3" /><h5>No response history!</h5><p>Your handled responses will appear here.</p></div>}
              {!loading && responseHistory.map(response => renderResponseCard(response, false))}
            </div>
          </Tab>
        </Tabs>
      </div>

      <Modal show={showResponseModal} onHide={() => { setShowResponseModal(false); setRegenerationError(""); }} size="lg">
        <Modal.Header closeButton className="modal-header-dark"><Modal.Title>Email Response Details</Modal.Title></Modal.Header>
        <Modal.Body className="modal-body-dark">
          <Alert variant="danger" show={!!regenerationError}>{regenerationError}</Alert>
          {selectedResponse && (
            <>
              <div className="original-email-info mb-3">
                <h6>Original Email:</h6>
                <div className="bg-dark p-3 rounded">
                  <strong>Subject:</strong> {selectedResponse.email_subject}<br />
                  <strong>To:</strong> {selectedResponse.sender_email}<br />
                  <strong>Summary:</strong> {selectedResponse.email_summary}
                </div>
              </div>
              <div className="response-info mb-3">
                <Badge bg={getAgentTypeColor(selectedResponse.agent_type)} className="type-badge me-2">{selectedResponse.agent_type?.replace('_', ' ')}</Badge>
                <Badge bg={getStatusColor(selectedResponse.status)} className="status-badge">{selectedResponse.status}</Badge>
              </div>
              <div className="generated-response-content">
                <h6>Generated Response:</h6>
                <div className="response-text">{selectedResponse.generated_response}</div>
              </div>
              {selectedResponse.user_suggestion && (
                <div className="user-suggestion-display mt-3">
                  <h6>Your Last Suggestion:</h6>
                  <div className="suggestion-text">{selectedResponse.user_suggestion}</div>
                </div>
              )}
              {selectedResponse.status === "pending" && (
                <div className="user-suggestion-section mt-4">
                  <Form.Group>
                    <Form.Label>Suggest changes (optional):</Form.Label>
                    <Form.Control as="textarea" rows={2} value={userSuggestion} onChange={(e) => setUserSuggestion(e.target.value)} placeholder="e.g., Make it more formal..."/>
                  </Form.Group>
                  <Form.Group className="mt-3">
                    <Form.Label>Attach document for more context (optional):</Form.Label>
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
              <Button variant="outline-warning" onClick={handleRegenerateResponse} disabled={!!actionLoading}>
                {actionLoading === "regenerate" ? <><Spinner animation="border" size="sm" className="me-2" />Regenerating...</> : <><FiRefreshCcw className="me-2" />Regenerate</>}
              </Button>
              <Button variant="outline-danger" onClick={() => handleResponseAction("reject")} disabled={!!actionLoading}>
                {actionLoading === "reject" ? <Spinner animation="border" size="sm" /> : <><FiX className="me-2" />Reject</>}
              </Button>
              <Button variant="success" onClick={() => handleResponseAction("approve")} disabled={!!actionLoading}>
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
