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
        self.task_type = 'sandbox' if opt['is_sandbox'] else 'live'
        self.scenariopath = os.path.join(
            opt['datapath'], opt['task'], opt['scenariopath']
        )

        self.outputpath = os.path.join(self.scenariopath, "output")

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

        # self.handler = MTurkHandler(opt=opt)
        # whether the mturker was matched to another mturker or not; initialized to false.
        self.agent.nego_got_matched = False

    def parley(self):
        """
        Get all the onboarding information and store it as attributes in the agent's object. 
        These will all be stored at the backend once the dialog is complete.
        """

        self.agent.agent_id = "Onboarding Agent"

        # request for survey code.
        sys_act = {}
        sys_act["id"] = 'System'
        sys_act[
            "text"
        ] = "Welcome onboard! Please complete the survey and enter the code on the left."
        sys_act["task_data"] = {
            #'board_status': "ONBOARD_FILL_SURVEY_CODE",
            #'survey_link': self.handler.input["survey_link"],
        }
        self.agent.observe(validate(sys_act))

        # get survey code.
        act = self.agent.act(timeout=self.opt["turn_timeout"])

        if act['episode_done']:
            # disconnect or mobile device or any other reason, but the turker has left.
            self.episodeDone = True  # this guy is done.
            return

        # we are done here.
        self.episodeDone = True

        """
        #has the code.
        #save it in the agent obj
        self.agent.nego_survey_link = self.handler.input["survey_link"]
        self.agent.nego_survey_code = act['task_data']['response']['qualtrics_code']

        #randomly choose values for this agent.
        
        values = ["High", "Medium", "Low"]
        random.shuffle(values)
        
        #Make food as Highest item
        
        #vals = ["Medium", "Low"]
        #random.shuffle(vals)
        #values = [vals[0], vals[1], "High"]
        
        #add info to the agent object
        self.agent.nego_issues = self.handler.input["issues"]
        self.agent.nego_items = self.handler.input["items"]
        self.agent.nego_values = values

        #request for preference reasons.
        #need to know which item is HIGH, which item is MEDIUM, which item is LOW.-> that's it.
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

        #get the responses.
        act = self.agent.act(timeout=self.opt["turn_timeout"])

        if(act['episode_done']):
            #disconnect or any other reason, but the turker has left.
            self.episodeDone = True #this guy is done.
            return
        
        #save response to agent obj
        self.agent.nego_onboarding_response = act['task_data']['response']

        #we are done here.
        self.episodeDone = True
        """


class MultiAgentDialogWorld(CrowdTaskWorld):
    """
    Basic world where each agent gets a turn in a round-robin fashion, receiving as
    input the actions of all other agents since that agent last acted.
    """

    def __init__(self, opt, agents=None, shared=None):
        # Add passed in agents directly.
        self.agents = agents
        self.acts = [None] * len(agents)
        self.episodeDone = False
        self.max_turns = opt.get("max_turns", 2)
        self.current_turns = 0
        self.send_task_data = opt.get("send_task_data", False)
        self.opt = opt
        for idx, agent in enumerate(self.agents):
            agent.agent_id = f"Chat Agent {idx + 1}"

    def parley(self):
        """
        For each agent, get an observation of the last action each of the other agents
        took.
        Then take an action yourself.
        """
        acts = self.acts
        self.current_turns += 1
        for index, agent in enumerate(self.agents):
            try:
                acts[index] = agent.act(timeout=self.opt["turn_timeout"])
                if self.send_task_data:
                    acts[index].force_set(
                        "task_data",
                        {
                            "last_acting_agent": agent.agent_id,
                            "current_dialogue_turn": self.current_turns,
                            "utterance_count": self.current_turns + index,
                        },
                    )
            except TypeError:
                acts[index] = agent.act()  # not MTurkAgent
            if acts[index]["episode_done"]:
                self.episodeDone = True
            for other_agent in self.agents:
                if other_agent != agent:
                    other_agent.observe(validate(acts[index]))
        if self.current_turns >= self.max_turns:
            self.episodeDone = True
            for agent in self.agents:
                agent.observe(
                    {
                        "id": "Coordinator",
                        "text": "Please fill out the form to complete the chat:",
                        "task_data": {
                            "respond_with_form": [
                                {
                                    "type": "choices",
                                    "question": "How much did you enjoy talking to this user?",
                                    "choices": [
                                        "Not at all",
                                        "A little",
                                        "Somewhat",
                                        "A lot",
                                    ],
                                },
                                {
                                    "type": "choices",
                                    "question": "Do you think this user is a bot or a human?",
                                    "choices": [
                                        "Definitely a bot",
                                        "Probably a bot",
                                        "Probably a human",
                                        "Definitely a human",
                                    ],
                                },
                                {"type": "text", "question": "Enter any comment here"},
                            ]
                        },
                    }
                )
                agent.act()  # Request a response
            for agent in self.agents:  # Ensure you get the response
                form_result = agent.act(timeout=self.opt["turn_timeout"])

    def prep_save_data(self, agent):
        """Process and return any additional data from this world you may want to store"""
        return {"example_key": "example_value"}

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
