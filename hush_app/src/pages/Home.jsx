// src/pages/Home.jsx
import React, { useEffect, useState, useContext } from "react";
import { useNavigate} from "react-router-dom";
import { Button } from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Home.css";
import Image from "../assets/Brand_logo.png";
import UserContext from "../UserContext/userContext";

function Home() {
  const navigate = useNavigate();
  const [logoVisible, setLogoVisible] = useState(false);
  const [logoFloatUp, setLogoFloatUp] = useState(false);
  const [buttonsVisible, setButtonsVisible] = useState(false);

  const { user } = useContext(UserContext);

  useEffect(() => {
    setTimeout(() => setLogoVisible(true), 500);       // Show logo
    setTimeout(() => setLogoFloatUp(true), 1800);      // Move logo up
    setTimeout(() => setButtonsVisible(true), 2400);   // Show buttons
  }, []);

  const handleClick = (type) => {
    switch(type) {
      case "summarize":
        navigate("/Email_Summarizer");
        break;
      case "smart-reply":
        navigate("/SmartReply");
        break;
      case "pending-responses":
        navigate("/PendingResponses");
        break;
      default:
        navigate("/Email_Summarizer");
    }
  };

  return (
    <div className="splash-wrapper">
      <div
        className={`logo-container ${logoVisible ? "visible" : ""} ${logoFloatUp ? "float-up" : ""}`}
        id="logo"
      >
        <img className="brand-image" src={Image} alt="Brand" />
        <h1 className="brand-text">Welcome {user?.name || "Guest"}!</h1>
        <h1 className="brand-text">Consent Secretary Agent</h1>
      </div>
      <div className={`button-container ${buttonsVisible ? "visible" : ""}`}>
        <div className="divider">
            <hr className="flex-grow-1" />
            <span className="px-2 text-white fw-lighter">AI Summary of Unread Emails</span>
            <hr className="flex-grow-1" />
        </div>
        <Button variant="outline-light" className="splash-btn" onClick={() => handleClick("summarize")}>
          View Email Summaries & Priorities
        </Button>
        
        <div className="divider">
            <hr className="flex-grow-1" />
            <span className="px-2 text-white fw-lighter">Generate Smart Replies</span>
            <hr className="flex-grow-1" />
        </div>
        <Button variant="outline-light" className="splash-btn" onClick={() => handleClick("smart-reply")}>
          Generate Smart Email Replies
        </Button>

        <div className="divider">
            <hr className="flex-grow-1" />
            <span className="px-2 text-white fw-lighter">Manage Your Responses</span>
            <hr className="flex-grow-1" />
        </div>
        <Button variant="outline-light" className="splash-btn" onClick={() => handleClick("pending-responses")}>
          View Pending & Sent Responses
        </Button>
      </div>
    </div>
  );
}

export default Home;