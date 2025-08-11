// src/pages/Home.jsx
import React, { useEffect, useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Alert } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Home.css";
import Image from "../assets/Brand_logo.png";
import UserContext from "../UserContext/userContext";
import KnowledgeBaseConsentModal from "../components/KnowledgeBaseConsentModal";
import axios from 'axios';
import { FiMoreVertical } from "react-icons/fi"; // Import the menu icon
import SidebarMenu from "../components/SlidebarMenu"; // Import the sidebar component

function Home() {
  const navigate = useNavigate();
  const [logoVisible, setLogoVisible] = useState(false);
  const [logoFloatUp, setLogoFloatUp] = useState(false);
  const [buttonsVisible, setButtonsVisible] = useState(false);
  const [isKbConsentModalOpen, setIsKbConsentModalOpen] = useState(false);
  const [error, setError] = useState(null);
  
  // State to manage the sidebar's visibility
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const { user } = useContext(UserContext);

  useEffect(() => {
    setTimeout(() => setLogoVisible(true), 500);
    // setTimeout(() => setLogoFloatUp(true), 1800);
    setTimeout(() => setButtonsVisible(true), 2400);
  }, []);

  const handleClick = (type) => {
    setError(null); // Clear previous errors
    switch (type) {
      case "summarize":
        navigate("/Email_Summarizer");
        break;
      case "smart-reply":
        setIsKbConsentModalOpen(true);
        break;
      case "pending-responses":
        navigate("/PendingResponses");
        break;
      default:
        navigate("/Email_Summarizer");
    }
  };

  const handleKbConsent = async () => {
    if (!user || !user.email) {
      setError("User information is not available. Please log in again.");
      setIsKbConsentModalOpen(false);
      return;
    }
    
    try {
      const response = await axios.post("http://localhost:8000/api/generate-kb-token", {
        user_email: user.email 
      });

      const { kb_consent_token } = response.data;

      if (kb_consent_token) {
        setIsKbConsentModalOpen(false);
        navigate("/SmartReply", { state: { kbConsentToken: kb_consent_token } });
      } else {
        throw new Error("Failed to retrieve a valid consent token from the server.");
      }
    } catch (err) {
      console.error("Error generating knowledge base token:", err);
      setError(err.response?.data?.detail || "Could not generate KB consent token.");
      setIsKbConsentModalOpen(false);
    }
  };

  const handleKbDecline = () => {
    setIsKbConsentModalOpen(false);
    navigate("/SmartReply");
  };

  return (
    <div className="splash-wrapper">
      {/* Sidebar Menu and Trigger Icon */}
      <div className="home-menu-trigger" onClick={() => setSidebarOpen(true)}>
        <FiMoreVertical size={24} />
      </div>
      <SidebarMenu isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Knowledge Base Consent Modal */}
      <KnowledgeBaseConsentModal
        isOpen={isKbConsentModalOpen}
        onConsent={handleKbConsent}
        onDecline={handleKbDecline}
      />
        
      {/* Display errors to the user */}
      {error && <Alert variant="danger" className="error-alert-home">{error}</Alert>}

      {/* Logo and welcome text */}
      <div
        className={`logo-container ${logoVisible ? "visible" : ""} ${
          logoFloatUp ? "float-up" : ""
        }`}
        id="logo"
      >
        <img className="brand-image" src={Image} alt="Brand" />
        <h1 className="brand-text">Welcome {user?.name || "Guest"}!</h1>
        <h1 className="brand-text">Consent Secretary Agent</h1>
      </div>

      {/* Action buttons */}
      <div className={`button-container ${buttonsVisible ? "visible" : ""}`}>
        {/* Summaries */}
        <div className="action-group">
          <div className="action-description">AI Summary of Unread Emails</div>
          <Button
            variant="outline-light"
            className="splash-btn"
            onClick={() => handleClick("summarize")}
          >
            View Email Summaries
          </Button>
        </div>

        {/* Smart Replies */}
        <div className="action-group">
          <div className="action-description">Generate Smart Replies</div>
          <Button
            variant="outline-light"
            className="splash-btn"
            onClick={() => handleClick("smart-reply")}
          >
            Generate Smart Email Replies
          </Button>
        </div>

        {/* Responses */}
        <div className="action-group">
          <div className="action-description">Manage Your Responses</div>
          <Button
            variant="outline-light"
            className="splash-btn"
            onClick={() => handleClick("pending-responses")}
          >
            View Pending & Sent Responses
          </Button>
        </div>

        {/* Knowledge Base */}
        <div className="action-group">
          <div className="action-description">Manage Your AI's Knowledge</div>
          <Button
            variant="outline-light"
            className="splash-btn"
            onClick={() => navigate("/knowledge-base")}
          >
            Manage Knowledge Base
          </Button>
        </div>
      </div>
    </div>
  );
}

export default Home;