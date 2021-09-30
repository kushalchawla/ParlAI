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
        self.block_qualification = opt['block_qualification']

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

    def compute_bonuses(self):
        """
        Basically, store the bonus for each agent in the object.
        """
        for agent in self.agents:
            agent.nego_final_base_pay = 0  # initialization
            agent.nego_performance_bonus = 0  # initialization
            agent.mean_nwords = -1  # initialization
            agent.dummy_wrong = -1  # initialization
            agent.work_quality = 'NA'  # initialization

        if not self.convo_is_finished:
            # no bonus needs to be paid, hence, the above variables will not be used. lets just return here
            return

        # bonus needs to be paid.

        # final_base_pay is fixed
        for agent in self.agents:
            agent.nego_final_base_pay = (
                2 - self.reward
            )  # 2 is the total base pay based on approx. 20 minutes time.. $6 per hour.

        """
        performance bonus
        H=0.41, M=0.33, L=0.26
        What do you have for every agent?
        agent.nego_items, agent.nego_values, agent.nego_issues, agent.nego_value2issue
        values are some permutation of ["High", "Medium", "Low"]
        
        self.last_submitted_deal_data: is also available in one of the acts, may not be correct for instance, if reject deal and then walk away.
        self.acts: list of all acts.
        
        Steps:
        1) The conversation is complete for sure. Figure out if the agreement was reached or someone walked away.
        2) If the agreement was reached, verify that self.last_submitted_deal_data contains the last submitted deal -> this should theoretically be true.
        3) figure out the individual bonuses.
        """

        # last two acts will be post-surveys, third-last act will tell whether the last deal was accepted or someone walked away.
        third_last_act = self.acts[-3]

        if third_last_act["text"] == "Walk-Away":
            # someone walked away, both will get flat rate for no agreement: $0.41
            for agent in self.agents:
                agent.nego_performance_bonus = 0.41  # rate for one High item.
        elif third_last_act["text"] == "Accept-Deal":

            # the deal was accepted; compute performance-based bonus. The deal will be in the fourth last act (with text Submit-Deal) or also stored in self.last_submitted_deal_data; directly use from the latter.
            # Who is you? Who is they? -> Whoever accepted the deal is "they".
            they_id = third_last_act["id"]

            # whatever is not they_id, is you_id
            you_id = "mturk_agent_1"
            if they_id == you_id:
                # wrong assumption; change required.
                you_id = "mturk_agent_2"

            # bonus for one item of each type
            H, M, L = 0.41, 0.33, 0.26

            # compute for each agent.
            for agent in self.agents:
                if agent.id == you_id:
                    # this is You guy, this is the guy who submitted the deal.
                    Hc = int(
                        self.last_submitted_deal_data["issue2youget"][
                            agent.nego_value2issue["High"]
                        ]
                    )
                    Mc = int(
                        self.last_submitted_deal_data["issue2youget"][
                            agent.nego_value2issue["Medium"]
                        ]
                    )
                    Lc = int(
                        self.last_submitted_deal_data["issue2youget"][
                            agent.nego_value2issue["Low"]
                        ]
                    )

                elif agent.id == they_id:
                    # this is They guy, this is the guy who accepted the deal.
                    Hc = int(
                        self.last_submitted_deal_data["issue2theyget"][
                            agent.nego_value2issue["High"]
                        ]
                    )
                    Mc = int(
                        self.last_submitted_deal_data["issue2theyget"][
                            agent.nego_value2issue["Medium"]
                        ]
                    )
                    Lc = int(
                        self.last_submitted_deal_data["issue2theyget"][
                            agent.nego_value2issue["Low"]
                        ]
                    )

                agent.nego_performance_bonus = H * Hc + M * Mc + L * Lc
        else:
            # something unknown happened, do not pay any performance bonus.
            pass

        # verification checks
        """
        1.	If average number of words per message is <= 2: DON’T PAY (ie pay just $0.05 as the bonus)
        2.	If average number of words per message is <= 4 and at least one (out of 2) verification questions is wrong: DON’T PAY.
        3.	If average number of words per message is <= 6 and both the verification questions are wrong: DON’T PAY.
        """
        for agent in self.agents:
            aid = agent.id

            # mean number of words in a message
            nwords = []
            for act in self.acts:
                if (
                    act['text']
                    not in [
                        'Submit-Deal',
                        'Accept-Deal',
                        'Reject-Deal',
                        'Walk-Away',
                        'Submit-Post-Survey',
                    ]
                ) and (act['id'] == aid):
                    nwords.append(len(act['text'].split()))
            mean_nwords = np.mean(nwords)

            # number of wrong dummy questions (0/1/2)
            dummy_wrong = 0
            for act in self.acts[-2:]:
                if (act['text'] == 'Submit-Post-Survey') and (act['id'] == aid):
                    if (
                        act['task_data']['response']['highest_item']
                        != agent.nego_value2issue['High']
                    ):
                        dummy_wrong += 1
                    if (
                        act['task_data']['response']['lowest_item']
                        != agent.nego_value2issue['Low']
                    ):
                        dummy_wrong += 1

            # rules
            agent.mean_nwords = mean_nwords
            agent.dummy_wrong = dummy_wrong
            agent.work_quality = 'pass'

            if mean_nwords <= 2:
                agent.work_quality = 'fail_R1'
            if (mean_nwords <= 4) and (dummy_wrong >= 1):
                agent.work_quality = 'fail_R2'
            if (mean_nwords <= 6) and (dummy_wrong == 2):
                agent.work_quality = 'fail_R3'

    def save_data(self):
        convo_finished = True
        bad_workers = []
        for ag in self.agents:
            if (
                ag.hit_is_abandoned
                or ag.hit_is_returned
                or ag.disconnected
                or ag.hit_is_expired
            ):
                bad_workers.append(ag.worker_id)
                convo_finished = False

        if convo_finished:
            self.convo_is_finished = True

        # compute bonus rewards
        self.compute_bonuses()

        agent_details = []
        for agent in self.agents:
            dat = {}
            dat["id"] = agent.id
            dat["worker_id"] = agent.worker_id
            dat["assignment_id"] = agent.assignment_id
            dat["hit_id"] = agent.hit_id
            dat[
                "nego_got_matched"
            ] = (
                agent.nego_got_matched
            )  # if this is true, this means the agent was paid the base pay for matching (typically $0.05)
            dat["survey_link"] = agent.nego_survey_link
            dat["survey_code"] = agent.nego_survey_code
            dat["issues"] = agent.nego_issues
            dat["items"] = agent.nego_items
            dat["values"] = agent.nego_values
            dat["value2issue"] = agent.nego_value2issue
            dat["onboarding_response"] = agent.nego_onboarding_response
            dat["initial_base_pay"] = (
                self.reward if agent.nego_got_matched else 0
            )  # ideally, else case would never arrive if we have reach this point.
            dat[
                "final_base_pay"
            ] = agent.nego_final_base_pay  # basically the total base pay ($2) - reward.
            dat[
                "performance_bonus"
            ] = (
                agent.nego_performance_bonus
            )  # this is the bonus amount which was poid to the mturker.
            dat["final_status"] = self.statuses[
                agent.id
            ]  # Normally, this will be END for both on completion.
            dat["work_quality"] = agent.work_quality
            dat["mean_nwords"] = agent.mean_nwords
            dat["dummy_wrong"] = agent.dummy_wrong
            agent_details.append(dat)

        """
        Store all data for this world/dialog
        Scenarios for each worker (mapped with Worker ID)
        AMT details of each worker
        complete dialog
        Pre-survey questions.
        Post-survey questions
        bad worker details.
        Meta data about the dialog/conversation
        """
        all_data = {
            'convo_is_finished': self.convo_is_finished,
            'world_tag': self.world_tag,
            'bad_workers': bad_workers,
            'acts': self.acts,  # contains all the returned acts.
            'turns': self.turns,  # includes system turns
            'workers': agent_details,
        }

        self.handler.save_conversation_data(all_data)

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

        # save data and call review_work (this is the recommended place for review_work as per Mephisto Issue #579)
        self.save_data()

        self.review_work()

    def review_work(self):
        global review_agent

        def review_agent(ag):
            if ag.nego_got_matched:
                ag.mephisto_agent.approve_work()
                print("Approved: ", ag.worker_id, ag.agent_id)

        Parallel(n_jobs=len(self.agents), backend='threading')(
            delayed(review_agent)(agent) for agent in self.agents
        )

        # Pay Bonus
        if self.convo_is_finished:
            for ag in self.agents:
                if ag.work_quality == 'pass':
                    total_bonus = round(
                        ag.nego_final_base_pay + ag.nego_performance_bonus, 2
                    )  # rounded to 2 decimal places.
                    reason = "The amount was computed based on whether the task was completed as per the instructions and the bonus payment rules. Thanks for participating!"
                else:
                    total_bonus = 0.05
                    reason = "Reduced bonus because of unsatisfactory work. Please note that not following the instructions properly affects the whole dialogue, even if your partner did high-quality work. Hence, it is very costly for us. If you think this is a mistake, please contact us. We would be very happy to discuss and pay you accordingly."
                tup = ag.mephisto_agent.get_worker().bonus_worker(
                    total_bonus, reason, ag.mephisto_agent.get_unit()
                )
                print(
                    "Bonus payment: worker_id, assignment_id, total_bonus, work_quality, paid tup: ",
                    ag.worker_id,
                    ag.assignment_id,
                    total_bonus,
                    ag.work_quality,
                    tup,
                )
        else:
            print("No bonus paid.")

        # soft-block the workers for future, if required.
        if self.convo_is_finished:
            for ag in self.agents:
                if ag.work_quality != 'pass':
                    # soft block this worker due to unsatisfactory work.
                    ag.mephisto_agent.get_worker().grant_qualification(
                        self.block_qualification
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
