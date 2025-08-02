import React, { useEffect, useState } from "react";
import { Card, Badge, Spinner, Accordion } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import { FiArrowLeft, FiMoreVertical } from "react-icons/fi";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Email_Summarizer.css";
import axios from "axios";
import SidebarMenu from "../components/SlidebarMenu";


function Email_Summarizer() {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    async function fetchEmailSummary() {
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
    }

    fetchEmailSummary();
  }, []);

  const getPriorityVariant = (level) => {
    switch (level) {
      case "High":
        return "danger";
      case "Medium":
        return "warning";
      case "Low":
        return "secondary";
      default:
        return "light";
    }
  };

  const [loadingMessageIndex, setLoadingMessageIndex] = useState(0);
  const loadingMessages = [
    "Summoning your inbox...",
    "Talking to the Gmail gods...",
    "Filtering out spam for you...",
    "Summarizing with style...",
    "Polishing those email nuggets...",
  ];

  useEffect(() => {
  let interval;
  if (loading) {
      interval = setInterval(() => {
        setLoadingMessageIndex((prevIndex) => (prevIndex + 1) % loadingMessages.length);
      }, 2000); // change message every 2 seconds
    }
    return () => clearInterval(interval); // cleanup
  }, [loading]);
  return (
    <div className="email-dark-wrapper">
      {/* Navbar */}
      <div className="top-navbar">
        <FiArrowLeft
          className="nav-icon"
          onClick={() => navigate("/home")}
          title="Back"
        />
        <h3 className="nav-title">Summarized Inbox</h3>
        <FiMoreVertical
          className="nav-icon"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          title="Menu"
        />
      </div>

      {/* Sidebar */}
      <SidebarMenu isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />


      {/* Email list */}
      <div className="email-list">
        {loading && (
        <div className="loading-spinner">
          <Spinner animation="border" />
          <p>{loadingMessages[loadingMessageIndex]}</p>
        </div>
      )}

        {error && <div className="error-message">{error}</div>}

        {!loading &&
          <Accordion defaultActiveKey="">
            {emails.map(({ id, sender, subject, summary, intent }, index) => (
              <Accordion.Item eventKey={index.toString()} key={id || index}>
                <Accordion.Header><div><div>Email number : {index+1}</div><div>Subject : {subject || "No Subject"}</div></div></Accordion.Header>
                <Accordion.Body>
                  <Card.Text className="email-summary-text">{summary || "No summary available."}</Card.Text>
                  <Badge className="intent-badge bg-white text-black">Intent: {intent || "Unknown"}</Badge>
                </Accordion.Body>
              </Accordion.Item>
            ))}
          </Accordion>
        }
      </div>
    </div>
  );
}

export default Email_Summarizer;
