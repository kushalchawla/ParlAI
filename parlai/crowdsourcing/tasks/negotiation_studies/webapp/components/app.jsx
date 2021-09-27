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
    const response_text = "Submitted";
    const response = {
        qualtrics_code: codeTextbox
    };

    tryMessageSend(response_text, response);
  }

  function handleSubmitReasons() {
    const response_text = "Submitted";
    const response = {
        high_reason: highReason,
        medium_reason: mediumReason,
        low_reason: lowReason,
    };

    tryMessageSend(response_text, response);
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

  function tryMessageSend(response_text, response) {
    setSending(true);

    const finalObj = {
      text: response_text,
      task_data: {response: response},
      id: agentId,
      episode_done: false,
    };
    
    sendMessage(finalObj).then(
      () => setSending(false)
    );
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
  let mainContent = <h3>Inside waiting task description</h3>;

  return (
    <div>
      {mainContent}
    </div>
  );
}

function MainTaskDescription({ mephistoContext, appContext }) {
  let mainContent = <h3>Inside main task description</h3>;

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