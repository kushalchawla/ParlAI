#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from parlai.crowdsourcing.utils.worlds import CrowdOnboardWorld, CrowdTaskWorld
from parlai.core.worlds import validate
from joblib import Parallel, delayed
import random
import os
import numpy as np
import json
import time
import csv
from mephisto.operations.logger_core import get_logger

logger = get_logger(name=__name__)


class MTurkHandler:
    """
    Handles all the I/O. 
    Basically, anything where you need to work with ParlAI/data/nego_data_collection/ directory.
    Includes input scenarios and output storage of dialogs and every associated data.
    """

    def __init__(self, opt):
        self._provider_type = opt['_provider_type']
        self.outputpath = os.path.join(opt['kc_managed_storage_dir'], "output")
        self.input = {
            "survey_link": "https://www.google.com/",  # link to qualtrics
            "issues": ["Food", "Water", "Firewood"],  # issue names
            "items": 3,  # number of items in each issue.
        }

    def save_conversation_data(self, all_data):
        """
        saves all data to a file for every conversation (ie every instantiation of the world)
        """

        # create output directory if does not exist.
        if not os.path.exists(self.outputpath):
            os.makedirs(self.outputpath)

        # get filename based on time
        if all_data["convo_is_finished"]:
            filename = os.path.join(
                self.outputpath,
                '{}_{}_{}.json'.format(
                    time.strftime("%Y%m%d-%H%M%S"),
                    np.random.randint(0, 1000),
                    self.task_type,
                ),
            )
        else:
            filename = os.path.join(
                self.outputpath,
                '{}_{}_{}_incomplete.json'.format(
                    time.strftime("%Y%m%d-%H%M%S"),
                    np.random.randint(0, 1000),
                    self.task_type,
                ),
            )

        with open(filename, 'w') as fp:
            json.dump(all_data, fp)
        print(
            "NegoDataCollection: "
            + all_data["world_tag"]
            + ': Conversation data successfully saved at {}.'.format(filename)
        )


class MultiAgentDialogOnboardWorld(CrowdOnboardWorld):
    def __init__(self, opt, agent):

        logger.info(f"Onboarding world initialization")
        logger.info(f"opt: {opt}")

        super().__init__(opt, agent)
        self.opt = opt

        self.handler = MTurkHandler(opt=opt)
        # whether the mturker was matched to another mturker or not; initialized to false.
        self.agent.nego_got_matched = False

    def parley(self):
        """
        Get all the onboarding information and store it as attributes in the agent's object. 
        These will all be stored at the backend once the dialog is complete.
        """
        logger.info("Onboarding Parley Begin")
        self.agent.agent_id = "Onboarding Agent"

        # request for survey code.
        sys_act = {}
        sys_act["id"] = 'System'
        sys_act[
            "text"
        ] = "Welcome onboard! Please complete the survey and enter the code on the left."
        sys_act["task_data"] = {
            'board_status': "ONBOARD_FILL_SURVEY_CODE",
            'survey_link': self.handler.input["survey_link"],
        }

        logger.info(f"sys_act: {sys_act}")
        self.agent.observe(validate(sys_act))

        # get survey code.
        act = self.agent.act(timeout=self.opt["turn_timeout"])

        if act['episode_done']:
            # disconnect or mobile device or any other reason, but the turker has left.
            self.episodeDone = True  # this guy is done.
            return

        logger.info(f"act: {act}")

        # has the code.
        # save it in the agent obj
        self.agent.nego_survey_link = self.handler.input["survey_link"]
        self.agent.nego_survey_code = act['task_data']['response']['qualtrics_code']

        # randomly choose values for this agent.

        values = ["High", "Medium", "Low"]
        random.shuffle(values)

        # Make food as Highest item
        # vals = ["Medium", "Low"]
        # random.shuffle(vals)
        # values = [vals[0], vals[1], "High"]

        # add info to the agent object
        self.agent.nego_issues = self.handler.input["issues"]
        self.agent.nego_items = self.handler.input["items"]
        self.agent.nego_values = values

        # request for preference reasons.
        # need to know which item is HIGH, which item is MEDIUM, which item is LOW.-> that's it.
        value2issue = {}
        for i in range(3):
            value2issue[values[i]] = self.agent.nego_issues[i]
        self.agent.nego_value2issue = value2issue

        sys_act = {}
        sys_act["id"] = 'System'
        sys_act["text"] = "Please complete the requested information on the left."
        sys_act["task_data"] = {
            'board_status': "ONBOARD_FILL_PREF_REASONS",
            'value2issue': self.agent.nego_value2issue,
        }
        self.agent.observe(validate(sys_act))

        # get the responses.
        act = self.agent.act(timeout=self.opt["turn_timeout"])

        if act['episode_done']:
            # disconnect or any other reason, but the turker has left.
            self.episodeDone = True  # this guy is done.
            return

        # save response to agent obj
        self.agent.nego_onboarding_response = act['task_data']['response']

        # send the final message to end the onboarding
        sys_act = {}
        sys_act["id"] = 'System'
        sys_act[
            "text"
        ] = "Thank you for your input! Please wait while we match you with another worker..."
        sys_act["episode_done"] = True
        sys_act["task_data"] = {}
        self.agent.observe(validate(sys_act))

        logger.info(f"survey code: {self.agent.nego_survey_code}")
        logger.info(f"nego_onboarding_response: {self.agent.nego_onboarding_response}")
        logger.info(f"self.agent.nego_survey_link: {self.agent.nego_survey_link}")
        logger.info(f"self.agent.nego_issues: {self.agent.nego_issues}")
        logger.info(f"self.agent.nego_items: {self.agent.nego_items}")
        logger.info(f"self.agent.nego_values: {self.agent.nego_values}")
        logger.info(f"self.agent.nego_value2issue: {self.agent.nego_value2issue}")
        # we are done here.
        self.episodeDone = True


class MultiAgentDialogWorld(CrowdTaskWorld):
    """
    Basic world where each agent gets a turn in a round-robin fashion, receiving as
    input the actions of all other agents since that agent last acted.
    """

    def __init__(self, opt, agents=None, shared=None):

        for idx, agent in enumerate(self.agents):
            agent.agent_id = f"mturk_agent_{idx + 1}"
        self.agent_ids = [
            agent.agent_id for agent in self.agents
        ]  # assume two agents with these ids coming in.
        if agents is not None:
            random.shuffle(agents)
            for agent in agents:
                assert agent.id in self.agent_ids
        self.reward = opt[
            'reward'
        ]  # base pay just for matching, this is automatically paid by MTurk as soon as we approve the task.
        self.agents = agents
        self.episodeDone = False
        self.first_turn = True
        self.turns = (
            0
        )  # this is basically # of calls to parley, will include system interactions. Hence, does not reflect the exact number of messages shared.
        self.handler = MTurkHandler(opt=opt)
        self.world_tag = (
            f"{time.strftime('%Y%m%d-%H%M%S')}_{np.random.randint(0, 1000)}"
        )
        self.convo_is_finished = False
        self.acts = (
            []
        )  # stores all the acts with messages, deals and post-surveys, in the exact sequence they are received.
        self.post_surveys = []
        self.last_reject_id = (
            ''
        )  # stores agent.id for the agent which sent the last reject offer: used by "CHAT" module, gets converted back to '' once used.
        self.an_agent_has_left = False
        self.last_submitted_deal_data = (
            {}
        )  # deal data for the last (most recent) submitted deal.
        self.num_msgs = (
            0
        )  # total number of messages shared in between Mturkers -> quite different from self.turns.
        self.buttons_activated = []  # needs to be done only once per MTurker
        self.timeout = opt[
            'turn_timeout'
        ]  # giving these many seconds for responding. -> this should be put somewhere in the guidelines.
        self.statuses = {}
        for agent_id in self.agent_ids:
            self.statuses[agent_id] = "CHAT"  # Initial status for both the agents.

    def parley(self):
        """
        Alternate turn taking, until both agents reach the END status.
        
        Define board status for each player -> this would help the front-end to show the appropriate content.
        Note that backend will only set a board status to the front-end when a change is required. otherwise it means to maintain the status quo.
        
        CHAT: The player is negotiating normally by typing messages. In this case, the left pane will show the agent's game details and provide buttons to enter the deal.
        DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER: The player clicked either no-agreement or agreement button to enter the deal and will now wait for the other guy to enter the deal.
        DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF: The other player has entered the deal. Now the chat will stop and you will be asked to enter the deal.
        ENTERING_POST_SURVEY: This player is now being asked to enter the post-survey. -> This guy was earlier in DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER and now when the wait is over, being asked to enter the post-survey questions.
        WAITING_FOR_POST_SURVEY_BY_OTHER: This guy was earlier either in DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF or in ENTERING_POST_SURVEY and is now waiting for the other guy to finish the post-survey. THIS IS THE LAST STATUS, after which the back-end will push the episode_done is TRUE for both agents. -> This is where ParlAI will automatically show the "Submit HIT" button to both and when the submit, the HIT will be over for the agents. -> At this point, final checks will be made, payments will be processed and data will be stored at the backend.
        END: The last status for both the agents which will call the episode_done for each agent. -> THIS IS NOT A SIGNAL TO KNOW WHETHER THE CHAT COMPLETED SUCCESSFULLY.
        This is how the status flow looks like for both the agents (which agent maps to which flow, will be decided on run-time):
        1) CHAT -> DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER -> ENTERING_POST_SURVEY -> WAITING_FOR_POST_SURVEY_BY_OTHER -> END
        2) CHAT -> DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF -> WAITING_FOR_POST_SURVEY_BY_OTHER -> ENTERING_POST_SURVEY -> END
        
        These do not flow independently and change in one agent's status, triggers the change in other agent's status.
        """
        self.turns += 1
        print(self.world_tag + ' is starting turn {}...'.format(self.turns))

        if self.first_turn:
            start_msg = True
            for agent in self.agents:
                assert self.statuses[agent.id] == "CHAT"
                action = {}
                action["id"] = 'System'
                if start_msg:
                    action[
                        "text"
                    ] = "Minimum 10 messages required so DON'T RUSH TO MAKE A DEAL. Chat freely BUT ONLY ON THE TOPIC. INQUIRE about partner's preferences, TRY HARD to get the best deals, CONVINCE THEM with your personal-life reasons and with EMOTION expression. WRITE COMPLETE sentences. NO PAYMENT for short/meaningless messages. IT'S NOW YOUR TURN. CHAT USING THE INPUT BOX BELOW (max 10 minutes to respond) ..."
                    start_msg = False
                else:
                    action[
                        "text"
                    ] = "Minimum 10 messages required so DON'T RUSH TO MAKE A DEAL. Chat freely BUT ONLY ON THE TOPIC. INQUIRE about partner's preferences, TRY HARD to get the best deals, CONVINCE THEM with your personal-life reasons and with EMOTION expression. WRITE COMPLETE sentences. NO PAYMENT for short/meaningless messages. WHEN IT'S YOUR TURN, CHAT USING THE INPUT BOX BELOW (max 10 minutes to respond) ..."
                action["task_data"] = {
                    'num_msgs': self.num_msgs,
                    'items': agent.nego_items,
                    'value2issue': agent.nego_value2issue,
                    'board_status': self.statuses[agent.id],
                }
                agent.observe(validate(action))
            self.first_turn = False

            # these turkers were matched. So update their nego_got_matched status.
            for agent in self.agents:
                agent.nego_got_matched = True
        else:
            # check if an agent has left
            if self.an_agent_has_left:
                # someone has left, shift both to END.
                for aa in self.agents:
                    action = {}
                    action["id"] = 'System'
                    self.statuses[aa.id] = 'END'
                    action[
                        "text"
                    ] = 'Your partner has unexpectedly left. You will still be paid the base amount. Please click the button below to finish this HIT.'
                    action["episode_done"] = True
                    action["task_data"] = {'board_status': self.statuses[aa.id]}
                    aa.observe(validate(action))
                # Now when both agents are in END, we can close the parley loop as well. Even if the above does not run, closing the parley loop ensures we are good.
                self.episodeDone = True
                return  # no need to proceed, we are done.

            for agent in self.agents:
                if self.statuses[agent.id] == 'CHAT':
                    # implies the other guy did not do anything yet. Will get both deal option and text option: as already done in the first_turn.
                    if self.last_reject_id != '' and self.last_reject_id != agent.id:
                        # A reject button was clicked by the partner agent, who needs to be prioritized for this one time.
                        self.last_reject_id = ''  # only need priority for one time.
                        continue  # this guy will go second.

                    # see if buttons need to be activated:
                    if self.num_msgs >= 10 and (agent.id not in self.buttons_activated):
                        action = {}
                        action["id"] = 'System'
                        action[
                            "text"
                        ] = 'Please dont rush but if you have agreed on a deal, you can submit from the left on your turn. Otherwise, keep chatting and try to make a deal. You can also walk away if you are unable to reach an agreement.'
                        action["task_data"] = {'num_msgs': self.num_msgs}
                        agent.observe(validate(action))
                        self.buttons_activated.append(agent.id)

                    act = agent.act(timeout=self.timeout)
                    self.acts.append(act)
                    if act['episode_done']:
                        # this guy disconnected
                        self.an_agent_has_left = True
                        return

                    if act['text'] not in ["Walk-Away", "Submit-Deal"]:
                        # a message was returned; otherwise a button was clicked.
                        self.num_msgs += 1  # increase number of messages.
                        for other_agent in self.agents:
                            if other_agent != agent:
                                # the other agent will maintain the status quo here and just observe the typed message.
                                other_agent.observe(validate(act))
                    elif act['text'] == "Submit-Deal":
                        # submitted the deal, requires storage + state change for both the agents.

                        # save deal data
                        self.last_submitted_deal_data = act['task_data']['response']
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            if aa.id == agent.id:
                                self.statuses[
                                    aa.id
                                ] = 'DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER'
                                action[
                                    "text"
                                ] = 'Thanks for entering the deal. Please wait for your partner to enter the deal.'
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            else:
                                self.statuses[
                                    aa.id
                                ] = 'DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF'
                                action[
                                    "text"
                                ] = "Your partner has entered their deal. Please either Accept, Reject or Walk Away (No agreement)."
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id],
                                    'deal_data': self.last_submitted_deal_data,
                                }
                            aa.observe(validate(action))
                    elif act['text'] == "Walk-Away":
                        # this agent clicked the walk away button, just head directly to the post-surveys.
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            if aa.id == agent.id:
                                self.statuses[
                                    aa.id
                                ] = 'WAITING_FOR_POST_SURVEY_BY_OTHER'
                                action[
                                    "text"
                                ] = 'You walked away and could not come to an agreement. Please wait for your partner to finish a few final questions.'
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            else:
                                self.statuses[aa.id] = 'ENTERING_POST_SURVEY'
                                action[
                                    "text"
                                ] = "Your partner has chosen to walk-away since you both could not come to an agreement. Please answer a few final questions on the left."
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id],
                                    'issues': agent.nego_issues,
                                }
                            aa.observe(validate(action))

                elif (
                    self.statuses[agent.id]
                    == 'DEAL_ENTERED_BY_MYSELF_AND_NOW_WAITING_FOR_OTHER'
                ):
                    # This guy is waiting for the other guy to enter the deal, hence, will keep on waiting.
                    pass
                elif (
                    self.statuses[agent.id]
                    == 'DEAL_ENTERED_BY_OTHER_AND_NOW_ENTERING_MYSELF'
                ):
                    # This guy will now be asked to enter the deal; requires state changes once the deal is entered.
                    act = agent.act(
                        timeout=self.timeout
                    )  # contains the deal output for sure.
                    self.acts.append(act)
                    if act['episode_done']:
                        # this guy disconnected
                        self.an_agent_has_left = True
                        return
                    # change states for both the agents, depending on which button was clicked.

                    if act['text'] == 'Reject-Deal':
                        # the deal was rejected, save agent_id and put both back in CHAT status.
                        self.last_reject_id = agent.id
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            if aa.id == agent.id:
                                self.statuses[aa.id] = 'CHAT'
                                action[
                                    "text"
                                ] = 'You rejected the deal. If there was a confusion, please chat again, finalize and then submit the deal. PLEASE CONTINUE CHATTING NOW ...'
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            else:
                                self.statuses[aa.id] = 'CHAT'
                                action[
                                    "text"
                                ] = "Your partner rejected the deal. If there was a confusion, please chat again, finalize and then submit the deal."
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            aa.observe(validate(action))
                    elif act['text'] == 'Accept-Deal':
                        # either the person walked away or accepted the deal, end negotiation and put in post survey mode.
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            if aa.id == agent.id:
                                self.statuses[
                                    aa.id
                                ] = 'WAITING_FOR_POST_SURVEY_BY_OTHER'
                                action[
                                    "text"
                                ] = 'Thanks for accepting the deal. Please wait for your partner to finish a few final questions.'
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            else:
                                self.statuses[aa.id] = 'ENTERING_POST_SURVEY'
                                action[
                                    "text"
                                ] = "Your partner has accepted your deal. Please answer a few final questions on the left."
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id],
                                    'issues': agent.nego_issues,
                                }
                            aa.observe(validate(action))
                    elif act['text'] == 'Walk-Away':
                        # either the person walked away or accepted the deal, end negotiation and put in post survey mode.
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            if aa.id == agent.id:
                                self.statuses[
                                    aa.id
                                ] = 'WAITING_FOR_POST_SURVEY_BY_OTHER'
                                action[
                                    "text"
                                ] = 'You walked away and could not come to an agreement. Please wait for your partner to finish a few final questions.'
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            else:
                                self.statuses[aa.id] = 'ENTERING_POST_SURVEY'
                                action[
                                    "text"
                                ] = "Your partner has chosen to walk-away since you both could not come to an agreement. Please answer a few final questions on the left."
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id],
                                    'issues': agent.nego_issues,
                                }
                            aa.observe(validate(action))
                elif self.statuses[agent.id] == 'WAITING_FOR_POST_SURVEY_BY_OTHER':
                    # This guy is waiting for the other guy to enter the deal, hence, will keep on waiting.
                    pass
                elif self.statuses[agent.id] == 'ENTERING_POST_SURVEY':
                    # this guy will now be asked to enter the post-survey; -> would require changes if the other guy is left.
                    act = agent.act(timeout=self.timeout)  # contains the post_survey.
                    self.acts.append(act)
                    if act['episode_done']:
                        # this guy disconnected
                        self.an_agent_has_left = True
                        return
                    self.post_surveys.append(agent.id)

                    if len(self.post_surveys) < 2:
                        # still one guy remaining; change states for both.
                        # change states for both the agents.
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            if aa.id == agent.id:
                                self.statuses[
                                    aa.id
                                ] = 'WAITING_FOR_POST_SURVEY_BY_OTHER'
                                action[
                                    "text"
                                ] = 'Thanks for answering the questions. Please wait for your partner to finish the final questions.'
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id]
                                }
                            else:
                                self.statuses[aa.id] = 'ENTERING_POST_SURVEY'
                                action[
                                    "text"
                                ] = "Your partner has answered their questions. Please answer your questions on the left."
                                action["task_data"] = {
                                    'board_status': self.statuses[aa.id],
                                    'issues': agent.nego_issues,
                                }
                            aa.observe(validate(action))
                    else:
                        # at this point both the agents have answered their final questions. -> Push both to END status
                        for aa in self.agents:
                            action = {}
                            action["id"] = 'System'
                            self.statuses[aa.id] = 'END'
                            action[
                                "text"
                            ] = 'Thanks for taking part in our study. Please click the button below to finish this HIT.'
                            action["episode_done"] = True
                            action["task_data"] = {'board_status': self.statuses[aa.id]}
                            aa.observe(validate(action))
                        # Now when both agents are in END, we can close the parley loop as well.
                        self.episodeDone = True
                elif self.statuses[agent.id] == 'END':
                    # just waiting for these guys to press the Done with this HIT button. Do nothing.
                    pass
                else:
                    # THIS MUST BE IN ERROR, LOG AND EXIT.
                    print(
                        "NegoDataCollection: ERROR-Status Mismatch, Agent Id, status: ",
                        agent.id,
                        self.statuses[agent.id],
                    )
                    self.episodeDone = True  # just to finish things

    def episode_done(self):
        return self.episodeDone

    def shutdown(self):
        """
        Shutdown all mturk agents in parallel, otherwise if one mturk agent is
        disconnected then it could prevent other mturk agents from completing.
        """
        global shutdown_agent

        def shutdown_agent(agent):
            try:
                agent.shutdown(timeout=None)
            except Exception:
                agent.shutdown()  # not MTurkAgent

        Parallel(n_jobs=len(self.agents), backend="threading")(
            delayed(shutdown_agent)(agent) for agent in self.agents
        )

    def review_work(self):
        global review_agent

        def review_agent(ag):
            if ag.nego_got_matched:
                ag.mephisto_agent.approve_work()
                print("Approved: ", ag.worker_id, ag.agent_id)

        Parallel(n_jobs=len(self.agents), backend='threading')(
            delayed(review_agent)(agent) for agent in self.agents
        )


def make_onboarding_world(opt, agent):
    return MultiAgentDialogOnboardWorld(opt, agent)


def validate_onboarding(data):
    """Check the contents of the data to ensure they are valid"""
    print(f"Validating onboarding data {data}")
    return True


def make_world(opt, agents):
    return MultiAgentDialogWorld(opt, agents)


def get_world_params():
    return {"agent_count": 2}
