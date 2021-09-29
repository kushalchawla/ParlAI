/*
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 */

import React from "react";
import ReactDOM from "react-dom";
import {
  FormControl,
  Button,
} from 'react-bootstrap';
import "bootstrap-chat/styles.css";

import { ChatApp, ChatMessage } from "bootstrap-chat";
import DefaultTaskDescription from "./index.js";

import { AGENT_STATUS } from "mephisto-task";

function RenderChatMessage({ message, mephistoContext, appContext, idx }) {
  const { agentId } = mephistoContext;
  const { currentAgentNames } = appContext.taskContext;

  return (
    <div onClick={() => alert("You clicked on message with index " + idx)}>
      <ChatMessage
        isSelf={message.id === agentId || message.id in currentAgentNames}
        agentName={
          message.id in currentAgentNames
            ? currentAgentNames[message.id]
            : message.id
        }
        message={message.text}
        taskData={message.task_data}
        messageId={message.message_id}
      />
    </div>
  );
}

function OnboardingTaskDescription({ mephistoContext, appContext }) {
  const { taskContext } = appContext;
  const { sendMessage, agentId } = mephistoContext;

  const boardStatus = taskContext['board_status'];
  const surveyLink = taskContext['survey_link'];
  const value2Issue = taskContext['value2issue'];
  
  //console.log("OnboardingTaskDescription", boardStatus, surveyLink, value2Issue);

  const [sending, setSending] = React.useState(false);
  const [codeTextbox, setCodeTextbox] = React.useState('');
  const [validityColor, setValidityColor] = React.useState('red');
  const [validityMsg, setValidityMsg] = React.useState('INVALID');
  const [codeValid, setCodeValid] = React.useState(false);
  const [highReason, setHighReason] = React.useState('');
  const [mediumReason, setMediumReason] = React.useState('');
  const [lowReason, setLowReason] = React.useState('');

  //internal function calls
  function handleSubmitCode() {
    const responseText = "Submitted";
    const response = {
        qualtrics_code: codeTextbox
    };

    tryMessageSend(responseText, response);
  }

  function handleSubmitReasons() {
    const responseText = "Submitted";
    const response = {
        high_reason: highReason,
        medium_reason: mediumReason,
        low_reason: lowReason,
    };

    tryMessageSend(responseText, response);
  }

  function handleCodeTextboxChange(val) {
    
    if((val.length === 10) && (!val.includes(' '))) {
      if(val[4] === 'T' && val[5] === '2') {
          setCodeTextbox(val);
          setValidityColor('green');
          setValidityMsg('VALID');
          setCodeValid(true);
      }
      else {
        setCodeTextbox(val);
        setValidityColor('red');
        setValidityMsg('INVALID');
        setCodeValid(false);
      }
    }
    else {
      setCodeTextbox(val);
      setValidityColor('red');
      setValidityMsg('INVALID');
      setCodeValid(false);
    }

  }

  function tryMessageSend(responseText, response) {
    
    if(!sending) {

      setSending(true);

      const finalObj = {
        text: responseText,
        task_data: {response: response},
        id: agentId,
        episode_done: false,
      };
      
      sendMessage(finalObj).then(
        () => setSending(false)
      );
    }

  }

  function countWords(str) {

    str = str.replace(/(^\s*)|(\s*$)/gi,"");
    str = str.replace(/[ ]{2,}/gi," ");
    str = str.replace(/\n /,"\n");
    return str.split(' ').length;

  }

  let mainContent = null;
  if(boardStatus == "ONBOARD_FILL_SURVEY_CODE") {
    mainContent = (
      <div id="ONBOARD_FILL_SURVEY_CODE">
          <div style={{ fontSize: '16px' }}>
              <span>- NOTE: Please use latest browsers to avoid any technical glitches. It is advisable to update the browser and restart the HIT.</span>
              <br /><br />
              <span>- Please turn on the system volume for notifications and the tutorial.</span>
              <br /><br />
              <span>- This is a <b>HIGH PAYING TASK</b>. You will be <b>blocked</b> if the conversation is effortless or not as per instructions.</span>
              <br /><br />
              <span>- <b>Do not reference the task, MTurk, money or discuss the number of messages</b> during the conversation.</span>
              <br /><br />
              <span>- <b>No racism, sexism or otherwise offensive comments</b>, or the submission will be rejected and reported to Amazon.</span>
          </div>
          <hr style={{ borderTop: '1px solid #555' }} />
          <span
            id="task-description"
            style={{ fontSize: '16px' }}>
          Please complete the survey and tutorial by clicking <a href={surveyLink} target='_blank'>here</a>. Copy the generated 10-character code (no spaces) in the input box below and submit. NOTE: you can save your code in case you get disconnected or are not matched but atleast watch the tutorial (<a href='https://youtu.be/7WLy8qjjMTY' target='_blank'>here</a>) every time before proceeding.
          </span>
          <br/>
          <div style={{ alignItems: 'center', display: 'flex' }}>
              <FormControl
              type="text"
              id="id_code_textbox"
              style={{
                width: '50%',
                height: '100%',
                float: 'left',
                fontSize: '12px',
              }}
              value={codeTextbox}
              placeholder="Enter Survey Code here"
              onChange={e => handleCodeTextboxChange(e.target.value)}
              disabled={sending}
            />
              <span id="id-validity-msg" style={{ color: validityColor, marginLeft: '2px' }}>{validityMsg}</span>
          </div>
            <br/>
          <Button
              className="btn btn-primary"
              style={{ fontSize: '16px', marginTop: '10px' }}
              id="id_submit_code"
              onClick={() => handleSubmitCode()}
              disabled={sending || !codeValid}
            >
              Submit Code
          </Button>
      </div>
  );
  } else if(boardStatus == "ONBOARD_FILL_PREF_REASONS") {
    
    let badReasonsMsg = "";
    
    if((countWords(highReason) < 5) || (countWords(mediumReason) < 5) || (countWords(lowReason) < 5)) {
        badReasonsMsg = "Please be more specific and write complete English sentences everywhere."
    }
    mainContent = (  
      <div id="ONBOARD_FILL_PREF_REASONS" style={{ fontSize: '16px' }}>
          <div>
              Your preference order and rules for bonus payments:
              <ol>
                <li>The <span style={{ color: 'blue' }}><b>{value2Issue['High']}</b></span> packages are worth the most. They are worth <span style={{ color: 'blue' }}><b>41 cents</b></span> a piece, so if you get <b>all three</b> of <span style={{ color: 'blue' }}><b>{value2Issue['High']}</b></span> packages, you’ll earn <span style={{ color: 'blue' }}><b>$1.23</b></span>.</li>

                <li>Each <span style={{ color: 'blue' }}><b>{value2Issue['Medium']}</b></span> package is worth <span style={{ color: 'blue' }}><b>only about 4/5</b></span> as much as a package of <span style={{ color: 'blue' }}><b>{value2Issue['High']}</b></span>.</li>

                <li>Each <span style={{ color: 'blue' }}><b>{value2Issue['Low']}</b></span> package is worth <span style={{ color: 'blue' }}><b>only about 3/5</b></span> as much as a package of <span style={{ color: 'blue' }}><b>{value2Issue['High']}</b></span>.</li>
              </ol>
              In total, you can earn <span style={{ color: 'blue' }}><b>$3</b></span> as bonus. If you WALK AWAY due to no agreement, you will be paid <span style={{ color: 'blue' }}><b>flat 41 cents</b></span> as bonus.
            <hr style={{ borderTop: '1px solid #555' }} />
              For your camping, you already have basic supplies and you will negotiate for additional packages. Below, we ask you to think of a real-life inspired reason, <b>justifying why you would need additional packages for your preferred items</b>.
              <br/>
              Think: Did you already get enough from home? Or do you need more for a specific hike/trip/emergency? Or anything else? <span style={{ color: 'blue' }}><b>BE CREATIVE!!!</b></span> <span style={{ color: 'blue' }}><b>BE SPECIFIC!!!</b></span> Write complete English sentences. <span style={{ color: 'blue' }}><b>You will later use these reasons when you negotiate.</b></span>
          </div>
          <hr style={{ borderTop: '1px solid #555' }} />  
          <div>
              Your <b>HIGHEST</b> priority item is <span style={{ color: 'blue' }}><b>{value2Issue['High']}</b></span>. Think of a reason why you would need <b>additional packages</b> of this item the most?
              <FormControl
              type="text"
              id="id_high_reason"
              style={{
                width: '80%',
                height: '100%',
                fontSize: '12px',
              }}
              value={highReason}
              placeholder="Enter here"
              onChange={e => setHighReason(e.target.value)}
              disabled={sending}
              />
          </div>
          <br /><br />
          <div>
              Your <b>MEDIUM</b> priority item is <span style={{ color: 'blue' }}><b>{value2Issue['Medium']}</b></span>. Think of a reason why you would need <b>additional packages</b> of this item second?
              <FormControl
              type="text"
              id="id_medium_reason"
              style={{
                width: '80%',
                height: '100%',
                fontSize: '12px',
              }}
              value={mediumReason}
              placeholder="Enter here"
              onChange={e => setMediumReason(e.target.value)}
              disabled={sending}
              />
          </div>
          <br /><br />
          <div>
              Your <b>LOWEST</b> priority item is <span style={{ color: 'blue' }}><b>{value2Issue['Low']}</b></span>. Think of a reason why you would prefer <b>additional packages</b> of this item the least?
              <FormControl
              type="text"
              id="id_low_reason"
              style={{
                width: '80%',
                height: '100%',
                fontSize: '12px',
              }}
              value={lowReason}
              placeholder="Enter here"
              onChange={e => setLowReason(e.target.value)}
              disabled={sending}
              />
          </div>
          <br /><br />
          <Button
              className="btn btn-primary"
              style={{ fontSize: '16px' }}
              id="id_submit_reasons"
              onClick={() => handleSubmitReasons()}
              disabled={highReason === '' || mediumReason === '' || lowReason === '' || (countWords(highReason) < 5) || (countWords(mediumReason) < 5) || (countWords(lowReason) < 5) || sending}
            >
              Submit Answers
          </Button>
          <div style={{color: 'red'}}>{badReasonsMsg}</div>
      </div>
  );
  }

  return (
    <div>
      {mainContent}
    </div>
  );
}

function WaitingTaskDescription({ mephistoContext, appContext }) {
  
  let mainContent = null;
  
  mainContent = (
    <div>
      <span
      id="task-description"
      style={{ fontSize: '16px' }}>
        Please wait while we connect you with a partner.
      </span>
      <hr style={{ borderTop: '1px solid #555' }} />
      <div style={{ fontSize: '16px' }}>
        <span style={{ color: 'blue' }}><b>Please do not contact us for not being matched with someone. Note that it is completely out of our control.</b></span>
        <br /><br />
        <span style={{ color: 'red' }}>- If you are still not matched after a long time and see 'Disconnected' or 'Reconnecting', try starting over, either right away or at another time. Don't worry, you can reuse your survey code. However, you may get a different preference order, so think of your reasons accordingly.</span>
        <br /><br />
        <span>- Please turn on the system volume for notifications and the tutorial.</span>
        <br /><br />
        <span>- This is a <b>HIGH PAYING TASK</b>.You will be <b>blocked</b> if the conversation is effortless or not as per instructions (ex: not using grammatically correct and complete English sentences, using repetitive sentences, and/or entering meaningless sentences to pass a chat turn).</span>
        <br /><br />
        <span style={{ color: 'red' }}>- <b>Do not reference the task, MTurk, money or discuss the number of messages</b> during the conversation.</span>
        <br /><br />
        <span>- <b>No racism, sexism or otherwise offensive comments</b>, or the submission will be rejected and reported to Amazon.</span>
      </div>
      <hr style={{ borderTop: '1px solid #555' }} />
    </div>
  );

  return (
    <div>
      {mainContent}
    </div>
  );
}

function MainTaskDescription({ mephistoContext, appContext }) {
  const { taskContext } = appContext;
  const { sendMessage, agentId } = mephistoContext;

  const boardStatus = taskContext['board_status'];
  const numMsgs = taskContext['num_msgs'];
  const numItems = taskContext['items'];
  const value2Issue = taskContext['value2issue'];
  const dealData = taskContext['deal_data'];
  const issues = taskContext['issues'];

  const [sending, setSending] = React.useState(false);
  
  const [youGet0, setYouGet0] = React.useState('-');
  const [youGet1, setYouGet1] = React.useState('-');
  const [youGet2, setYouGet2] = React.useState('-');

  const [theyGet0, setTheyGet0] = React.useState('-');
  const [theyGet1, setTheyGet1] = React.useState('-');
  const [theyGet2, setTheyGet2] = React.useState('-');

  const [likeness, setLikeness] = React.useState('-');
  const [satisfaction, setSatisfaction] = React.useState('-');
  
  const [highestItem, setHighestItem] = React.useState('-');
  const [lowestItem, setLowestItem] = React.useState('-');

  const [partnerHighestItem, setPartnerHighestItem] = React.useState('-');
  const [partnerLowestItem, setPartnerLowestItem] = React.useState('-');

  const [feedback, setFeedback] = React.useState('');

  //internal function calls
  function handleWalkAway() {
    const responseText = "Walk-Away";
    const response = {
        data: "walk_away"
    };
    
    //console.log("KC: no argument: ", responseText, response);
    tryMessageSend(responseText, response);
  }
  
  function handleChatUpdate0(val) {
    if(val === '-') {
      setYouGet0(val);
      setTheyGet0(val);
    } else {
      setYouGet0(val);
      setTheyGet0((numItems-parseInt(val)).toString());
    }
  }
    
  function handleChatUpdate1(val) {
    if(val === '-') {
      setYouGet1(val);
      setTheyGet1(val);
    } else {
      setYouGet1(val);
      setTheyGet1((numItems-parseInt(val)).toString());
    }
  }  

  function handleChatUpdate2(val) {
    if(val === '-') {
      setYouGet2(val);
      setTheyGet2(val);
    } else {
      setYouGet2(val);
      setTheyGet2((numItems-parseInt(val)).toString());
    }
  }  
    
  function handleSubmitDeal() {
    const responseText = "Submit-Deal";
    
    const issue2youget = {};    
    issue2youget[value2Issue["High"]] = youGet0;
    issue2youget[value2Issue["Medium"]] = youGet1;
    issue2youget[value2Issue["Low"]] = youGet2;
    
    const issue2theyget = {};    
    issue2theyget[value2Issue["High"]] = theyGet0;
    issue2theyget[value2Issue["Medium"]] = theyGet1;
    issue2theyget[value2Issue["Low"]] = theyGet2;

    const response = {
        "issue2youget": issue2youget,
        "issue2theyget": issue2theyget,
    };
    
    //console.log("KC: Submit deal: ", responseText, response);
    tryMessageSend(responseText, response);
  }
    
  function handleAcceptDeal() {
    const responseText = "Accept-Deal";
    const response = {
        data: "accept_deal"
    };
    
    //console.log("KC: Submit deal: ", responseText, response);
    tryMessageSend(responseText, response);
  }
    
  function handleRejectDeal() {
    const responseText = "Reject-Deal";
    const response = {
        data: "reject_deal"
    };
    
    //console.log("KC: Submit deal: ", responseText, response);
    tryMessageSend(responseText, response);
  }

  function handlePostSurvey() {
    const responseText = "Submit-Post-Survey";
    const response = {
        likeness: likeness,
        satisfaction: satisfaction,
        highest_item: highestItem,
        lowest_item: lowestItem,
        partner_highest_item: partnerHighestItem,
        partner_lowest_item: partnerLowestItem,
        feedback: feedback
    };
    //console.log("KC: post-survey: ", responseText, response);
    tryMessageSend(responseText, response);
  }
  
  function tryMessageSend(responseText, response) {

    if(!sending && (this.props.chat_state === 'text_input')) {
      
      setSending(true);

      const finalObj = {
        text: responseText,
        task_data: {response: response},
        id: agentId,
        episode_done: false,
      };
      
      sendMessage(finalObj).then(
        () => setSending(false)
      );

    }
  }

  let mainContent = null;

  if(boardStatus === "CHAT") {
    
    let submitDealFinalMsg = [];
    let walkAwayFinalMsg = [];
        
    if(this.props.chat_state != 'text_input') {
        submitDealFinalMsg.push("Wait for your turn");
        walkAwayFinalMsg.push("Wait for your turn");
    }
      
    if(numMsgs < 10) {
        submitDealFinalMsg.push("Min 10 messages required");
        walkAwayFinalMsg.push("Min 10 messages required");
    }
      
    if((youGet0 === '-') || (youGet1 === '-') || (youGet2 === '-')) {
        submitDealFinalMsg.push("Deal must be entered above");
    }
    
    submitDealFinalMsg = submitDealFinalMsg.join(" | ");
    walkAwayFinalMsg = walkAwayFinalMsg.join(" | ");
    
    mainContent = (
      <div id="CHAT" style={{ fontSize: '16px' }}>
            <span>- Each item has <span style={{ color: 'blue' }}><b>{numItems}</b></span> packages.</span>
            <br />
            <span>- <span style={{ color: 'blue' }}><b>DO NOT RUSH TO MAKE A DEAL.</b></span>You must chat for atleast 10 messages.</span>
            <br />
            <span>- Chat freely but always <span style={{ color: 'blue' }}><b>STAY ON THE TOPIC</b></span>.</span>
            <br />    
            <span>- You should <span style={{ color: 'blue' }}><b>INQUIRE</b></span> about partner's preferences.</span>
            <br />
            <span>- Try to <span style={{ color: 'blue' }}><b>CONVINCE</b></span> them with your personal-life reasons or <span style={{ color: 'blue' }}><b>EMOTION</b></span> expression.</span> 
            <br />
            <span>- <span style={{ color: 'blue' }}><b>TRY HARD</b></span> to get the best deals.</span>
            <br />
            <span>- <span style={{ color: 'blue' }}><b>WRITE COMPLETE</b></span> sentences.</span>
            <br />
            <span>- <span style={{ color: 'blue' }}><b>NO PAYMENT</b></span> for short/meaningless messages.</span>
            <br />
            <span>- <span style={{ color: 'red' }}><b>IF THE SCREEN FLICKERS</b></span>, try zooming in and out. This can happen for older browsers.</span>
            <br />
          <hr style={{ borderTop: '1px solid #555' }} />
          <Table bordered hover size="sm" style={{ backgroundColor: 'white' }}>
            <thead>
              <tr>
                <th>Value</th>
                <th>Item</th>
                <th>Packages you get</th>
                <th>Packages they get</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>High</td>
                  <td>{value2Issue['High']}</td>
                <td>
                    <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => handleChatUpdate0(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                      defaultValue={youGet0}  
                  >
                      <option>-</option>
                      <option>0</option>
                      <option>1</option>
                      <option>2</option>
                      <option>3</option>
                    </FormControl>
                  </td>
                <td>{theyGet0}</td>
              </tr>
              <tr>
                <td>Medium</td>
                  <td>{value2Issue['Medium']}</td>
                <td>
                    <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => handleChatUpdate1(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                      defaultValue={youGet1}  
                  >
                      <option>-</option>
                      <option>0</option>
                      <option>1</option>
                      <option>2</option>
                      <option>3</option>
                    </FormControl>
                  </td>
                <td>{theyGet1}</td>
              </tr>
              <tr>
                <td>Low</td>
                  <td>{value2Issue['Low']}</td>
                <td>
                    <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => handleChatUpdate2(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                      defaultValue={youGet2}  
                  >
                      <option>-</option>
                      <option>0</option>
                      <option>1</option>
                      <option>2</option>
                      <option>3</option>
                    </FormControl>
                  </td>
                <td>{theyGet2}</td>
              </tr>
            </tbody>
          </Table>
          <div style={{ alignItems: 'center', display: 'flex' }}>  
              <Button
                  className="btn btn-primary"
                  style={{ fontSize: '16px'}}
                  id="id_submit_deal"
                  onClick={() => handleSubmitDeal()}
                  disabled={sending || (this.props.chat_state != 'text_input') || (youGet0 === '-') || (youGet1 === '-') || (youGet2 === '-') || (numMsgs < 10)}
                >
                  Submit Deal
              </Button>
              <span style={{ color: 'red', marginLeft: '2px' }}>{submitDealFinalMsg}</span>
          </div>
          <hr style={{ borderTop: '1px solid #555' }} />
          <hr style={{ borderTop: '1px solid #555' }} />
          <div style={{ alignItems: 'center', display: 'flex' }}>
              <Button
                  className="btn btn-primary"
                  style={{ fontSize: '16px', backgroundColor: 'red'}}
                  id="id_walk_away"
                  onClick={() => handleWalkAway()}
                  disabled={sending || (this.props.chat_state != 'text_input') || (numMsgs < 10)}
                >
                  Walk Away (Ends Negotiation)
              </Button>
              <span style={{ color: 'red', marginLeft: '2px' }}>{walkAwayFinalMsg}</span>
            </div>
      </div>
  );
  } else if (boardStatus === "DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER") {
      mainContent = (
          <div id="DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER" style={{ fontSize: '16px' }}> 
              Please wait for your partner to enter the deal.
          </div>
      );
  } else if (boardStatus === "DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF") {
      mainContent = (
          <div id="DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF" style={{ fontSize: '16px' }}>
          <Table bordered hover size="sm" style={{ backgroundColor: 'white' }}>
            <thead>
              <tr>
                <th>Value</th>
                <th>Item</th>
                <th>Packages you get</th>
                <th>Packages they get</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>High</td>
                <td>{value2Issue['High']}</td>
                <td>{dealData["issue2theyget"][value2Issue['High']]}</td>
                <td>{dealData["issue2youget"][value2Issue['High']]}</td>
              </tr>
              <tr>
                <td>Medium</td>
                <td>{value2Issue['Medium']}</td>
                <td>{dealData["issue2theyget"][value2Issue['Medium']]}</td>
                <td>{dealData["issue2youget"][value2Issue['Medium']]}</td>
              </tr>
              <tr>
                <td>Low</td>
                <td>{value2Issue['Low']}</td>
                <td>{dealData["issue2theyget"][value2Issue['Low']]}</td>
                <td>{dealData["issue2youget"][value2Issue['Low']]}</td>
              </tr>
            </tbody>
          </Table>
              <span style={{ color: 'blue' }}><b>Your partner has entered the above deal. Please either Accept, Reject (if not what you agreed) or Walk Away (No agreement).</b></span>
              <div>
                  <Button
                      className="btn btn-primary"
                      style={{ fontSize: '16px', marginRight: '10px', marginBottom: '10px' }}
                      id="id_accept_deal"
                      onClick={() => handleAcceptDeal()}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                    >
                      Accept Deal (Ends Negotiation)
                  </Button>
                  <Button
                      className="btn btn-primary"
                      style={{ fontSize: '16px' }}
                      id="id_reject_deal"
                      onClick={() => handleRejectDeal()}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                    >
                      Reject Deal (Continues Negotiation)
                  </Button>
              </div>
              <hr style={{ borderTop: '1px solid #555' }} />
              <hr style={{ borderTop: '1px solid #555' }} />
              <Button
                  className="btn btn-primary"
                  style={{ fontSize: '16px', backgroundColor: 'red' }}
                  id="id_walk_away"
                  onClick={() => handleWalkAway()}
                  disabled={sending || (this.props.chat_state != 'text_input')}
                >
                  Walk Away (Ends Negotiation)
              </Button>
          </div>
      );
  } else if (boardStatus === "WAITING_FOR_POST_SURVEY_BY_OTHER") {
      mainContent = (
          <div id="WAITING_FOR_POST_SURVEY_BY_OTHER" style={{ fontSize: '16px' }}>
              Please wait for your partner to finish the final questions.
          </div>
      );
  } else if (boardStatus === "ENTERING_POST_SURVEY") {
      
      let postSurveyValidity = null;
        if((likeness === '-') || (satisfaction === '-') || (highestItem === '-') || (lowestItem === '-') || (partnerHighestItem === '-') || (partnerLowestItem === '-')) {
            postSurveyValidity = (
                <span id="id-post-survey-validity-msg" style={{ color: 'red', marginLeft: '2px' }}>Answer all questions above to submit</span>
            );
        } else {
            postSurveyValidity = (
                <span id="id-post-survey-validity-msg" style={{ color: 'red', marginLeft: '2px' }}></span>
            );
        }
      mainContent = (
          <div id="ENTERING_POST_SURVEY" style={{ fontSize: '16px' }}> 
              <div>Please answer a few final questions:</div>
              <br />
              <div>
                  How much do you like your opponent?
                  <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => setLikeness(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  >
                      <option>-</option>
                      <option>Extremely dislike</option>
                      <option>Slightly dislike</option>
                      <option>Undecided</option>
                      <option>Slightly like</option>
                      <option>Extremely like</option>
                  </FormControl>
              </div>
              <br />
              <div>
                  How satisfied are you with the negotiation outcome?
                  <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => setSatisfaction(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  >
                      <option>-</option>
                      <option>Extremely dissatisfied</option>
                      <option>Slightly dissatisfied</option>
                      <option>Undecided</option>
                      <option>Slightly satisfied</option>
                      <option>Extremely satisfied</option>
                  </FormControl>
              </div>
              <br />
              <div>
                  What was your <b>Highest</b> priority item?
                  <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e =>  setHighestItem(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  >
                      <option>-</option>
                      <option>{issues[0]}</option>
                      <option>{issues[1]}</option>
                      <option>{issues[2]}</option>
                  </FormControl>
              </div>
              <br />
              <div>
                  What was your <b>Lowest</b> priority item?
                  <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => setLowestItem(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  >
                      <option>-</option>
                      <option>{issues[0]}</option>
                      <option>{issues[1]}</option>
                      <option>{issues[2]}</option>
                  </FormControl>
              </div>
              <br />
              <div>
                  What do you think was your <b> Partner's Highest</b> priority item?
                  <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => setPartnerHighestItem(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  >
                      <option>-</option>
                      <option>{issues[0]}</option>
                      <option>{issues[1]}</option>
                      <option>{issues[2]}</option>
                  </FormControl>
              </div>
              <br />
              <div>
                  What do you think was your <b>Partner's Lowest</b> priority item?
                  <FormControl
                      componentClass="select"
                      style={{ fontSize: '16px' }}
                      onChange={e => setPartnerLowestItem(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  >
                      <option>-</option>
                      <option>{issues[0]}</option>
                      <option>{issues[1]}</option>
                      <option>{issues[2]}</option>
                  </FormControl>
              </div>
              <br />
              <div>
                  Provide your feedback below (This is the last time we are running these HITs. Final thoughts?). Please keep it brief, your partner is waiting.
                  <FormControl
                      type="text"
                      style={{
                        width: '80%',
                        height: '100%',
                        fontSize: '12px',
                      }}
                      value={feedback}
                      placeholder="Enter here"
                      onChange={e => setFeedback(e.target.value)}
                      disabled={sending || (this.props.chat_state != 'text_input')}
                  />
              </div>
              <br/> <br/>
              <div style={{ alignItems: 'center', display: 'flex' }}>
                  <Button
                  className="btn btn-primary"
                  style={{ fontSize: '16px', float: 'left' }}
                  id="id_post_survey"
                  onClick={() => handlePostSurvey()}
                  disabled={sending || (this.props.chat_state != 'text_input') || likeness === '-' || satisfaction === '-' || highestItem === '-' || lowestItem === '-' || partnerHighestItem === '-' || partnerLowestItem === '-'}
                >
                  Submit
                  </Button>
                  {postSurveyValidity}
              </div>
          </div>
      );
  } else if (boardStatus === "END") {
      mainContent = (
          <div id="END" style={{ fontSize: '16px' }}>
              Thanks for taking part in our study. Please click the button on the right to finish this HIT.
          </div>
      );
  }

  return (
    <div>
      {mainContent}
    </div>
  );
}

function MainApp() {
  return (
    <ChatApp
      renderMessage={({ message, idx, mephistoContext, appContext }) => {
        
        return (
        <RenderChatMessage
          message={message}
          mephistoContext={mephistoContext}
          appContext={appContext}
          idx={idx}
          key={message.message_id + "-" + idx}
        />
        );
      }
    }
      renderSidePane={({ mephistoContext, appContext }) => {
        const { taskConfig, agentStatus } = mephistoContext;

        let mainContent = null;

        if(agentStatus == AGENT_STATUS.ONBOARDING) {
          mainContent = (
            <OnboardingTaskDescription
              mephistoContext = {mephistoContext}
              appContext = {appContext}
            />
          );
        }
        else if(agentStatus == AGENT_STATUS.WAITING) {
          mainContent = (
            <WaitingTaskDescription
              mephistoContext = {mephistoContext}
              appContext = {appContext}
            />
          );
        }
        else if(agentStatus == AGENT_STATUS.IN_TASK) {
          mainContent = (
            <MainTaskDescription
              mephistoContext = {mephistoContext}
              appContext = {appContext}
            />
          );
        }
        else {
          //keep it empty for now
        }

        //console.log("renderSidePane", agentStatus, mainContent);

        return (
          <DefaultTaskDescription
            chatTitle={taskConfig.chat_title}
            taskDescriptionHtml={taskConfig.task_description}
          >
            {mainContent}
          </DefaultTaskDescription>
        );
      }
    }
    />
  );
}

ReactDOM.render(<MainApp />, document.getElementById("app"));