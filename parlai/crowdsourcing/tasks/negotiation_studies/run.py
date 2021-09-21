#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import os
from mephisto.operations.operator import Operator
from mephisto.tools.scripts import load_db_and_process_config
from mephisto.abstractions.blueprints.parlai_chat.parlai_chat_blueprint import (
    BLUEPRINT_TYPE,
    SharedParlAITaskState,
)

import hydra
from omegaconf import DictConfig, MISSING
from dataclasses import dataclass, field
from typing import List, Any
import copy
import numpy as np

TASK_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

defaults = [
    "_self_",
    {"mephisto/blueprint": BLUEPRINT_TYPE},
    {"mephisto/architect": "heroku"},
    {"mephisto/provider": "mturk_sandbox"},
    "conf/base",
    {"conf": "develop"},
]

from mephisto.operations.hydra_config import RunScriptConfig, register_script_config


@dataclass
class TestScriptConfig(RunScriptConfig):
    defaults: List[Any] = field(default_factory=lambda: defaults)
    task_dir: str = TASK_DIRECTORY
    num_turns: int = field(
        default=3,
        metadata={"help": "Number of turns before a conversation is complete"},
    )
    onboarding_turn_timeout: int = field(
        default=300,
        metadata={
            "help": "Maximum response time for onboarding response. This is higher since it involves filling in the pre-survey."
        },
    )
    turn_timeout: int = field(
        default=300,
        metadata={
            "help": "Maximum response time before kicking "
            "a worker out, default 300 seconds"
        },
    )

    kc_managed_storage_dir: str = field(
        default=MISSING, metadata={"help": "self-managed storage directory"}
    )


register_script_config(name="scriptconfig", module=TestScriptConfig)


@hydra.main(config_path="hydra_configs", config_name="scriptconfig")
def main(cfg: DictConfig) -> None:
    db, cfg = load_db_and_process_config(cfg, print_config=True)
    cfg.mephisto.blueprint.onboarding_qualification = f"{cfg.mephisto.blueprint.onboarding_qualification}_{np.random.randint(0, 10000)}"
    print(f"in main: cfg: ", cfg)

    world_opt = {
        "num_turns": cfg.num_turns,
        "turn_timeout": cfg.turn_timeout,
        "kc_managed_storage_dir": cfg.kc_managed_storage_dir,
        "_provider_type": cfg.mephisto.provider._provider_type,
    }

    # update time out for the onboarding responses.
    onboarding_world_opt = copy.deepcopy(world_opt)
    onboarding_world_opt["turn_timeout"] = cfg.onboarding_turn_timeout

    custom_bundle_path = cfg.mephisto.blueprint.get("custom_source_bundle", None)
    if custom_bundle_path is not None:
        assert os.path.exists(custom_bundle_path), (
            "Must build the custom bundle with `npm install; npm run dev` from within "
            f"the {TASK_DIRECTORY}/webapp directory in order to demo a custom bundle "
        )
        world_opt["send_task_data"] = True

    shared_state = SharedParlAITaskState(
        world_opt=world_opt, onboarding_world_opt=onboarding_world_opt
    )

    operator = Operator(db)

    operator.validate_and_run_config(cfg.mephisto, shared_state)
    operator.wait_for_runs_then_shutdown(skip_input=True, log_rate=30)


if __name__ == "__main__":
    main()
