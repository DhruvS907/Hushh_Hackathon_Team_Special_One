// App.js
import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import UserContext from "./UserContext/userContext";
import Splash from "./pages/Splash";
import SignIn from "./pages/signin";
import SignUp from "./pages/signup";
import Home from "./pages/Home";
import Email_Summarizer from "./pages/Email_Summarizer";
import FormSignup from "./pages/forms_after_signup";
import { FiAlertCircle } from "react-icons/fi";
import SmartReply from "./pages/SmartReply";
import PendingResponses from "./pages/PendingResponses";

function App() {
  const [user, setUser] = useState(() => {
    // Load user from localStorage on first render
    const stored = localStorage.getItem("user");
    return stored ? JSON.parse(stored) : { name: "", email: "", consentToken: null };
  });

  // Update localStorage when user state changes
  useEffect(() => {
    localStorage.setItem("user", JSON.stringify(user));
  }, [user]);

  return (
    <BrowserRouter>
      <UserContext.Provider value={{ user, setUser }}>
        <ToastContainer
          position="top-center"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnHover={false}
          draggable
          theme="dark"
          limit={1}
          icon={({ type }) =>
            type === "error" ? (
              <FiAlertCircle style={{ color: "white", fontSize: "1.2em" }} />
            ) : undefined
          }
        />
        <Routes>
              {/* Authentication Routes */}
              <Route path="/" element={<Splash />} />
              <Route path="/signin" element={<SignIn />} />
              <Route path="/signup" element={<SignUp />} />
              <Route path="/FormSignup" element={<FormSignup />} />
              
              {/* Main Application Routes */}
              <Route path="/home" element={<Home />} />
              <Route path="/Email_Summarizer" element={<Email_Summarizer />} />
              <Route path="/SmartReply" element={<SmartReply />} />
              <Route path="/PendingResponses" element={<PendingResponses />} />
              
              {/* Backward compatibility */}
              <Route path="/Send_Replies" element={<SmartReply />} />
            </Routes>
      </UserContext.Provider>
    </BrowserRouter>
  );
}

export default App;