# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys
import logging

import traceback
import jsonschema

from st2common.util import schema
from st2common.constants import action as action_constants
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE


LOG = logging.getLogger(__name__)


def _validate_runner(runner_schema, result):
    LOG.debug("Validating runner output: %s", runner_schema)

    runner_schema = {
        "type": "object",
        "properties": runner_schema,
        "additionalProperties": False,
    }

    schema.validate(result, runner_schema, cls=schema.get_validator("custom"))


def _prepare_action_schema(action_schema):
    """
    Prepares the final action schema.

    :param action_schema: action schema of a action execution ouput.
    :return: final_action_schema: along with type and additionalProperties flag.
    :rtype: ``dict``.
    """

    final_action_schema = {
        "type": "object",
        "properties": action_schema,
        "additionalProperties": False,
    }

    return final_action_schema


def output_schema_secret_masking(result, output_key, action_schema):
    """
    Masks the secret parameters provided in output schema.

    :param result: result of the action execution.
    :param output_key: key for parsing specific result from action execution result.
    :param action_schema: action schema of a action execution ouput.
    :return: final_result: to be displayed in CLI or Web UI with masked secrets.
    :rtype: ``dict``.
    """

    final_result = result[output_key]

    final_action_schema = action_schema

    # accessing parameters marked secret as true in the output_schema in
    # action_schema and masking them for the final result of the output
    for key in final_action_schema["properties"]:
        if final_action_schema.get("properties", {}).get(key).get("secret", False):
            final_result[key] = MASKED_ATTRIBUTE_VALUE

    return final_result


def _validate_action(action_schema, result, output_key):
    LOG.debug("Validating action output: %s", action_schema)

    action_schema = _prepare_action_schema(action_schema)
    final_result = output_schema_secret_masking(result=result,
                                                output_key=output_key,
                                                action_schema=action_schema)

    schema.validate(final_result, action_schema, cls=schema.get_validator("custom"))


def validate_output(runner_schema, action_schema, result, status, output_key):
    """Validate output of action with runner and action schema."""
    try:
        LOG.debug("Validating action output: %s", result)
        LOG.debug("Output Key: %s", output_key)
        if runner_schema:
            _validate_runner(runner_schema, result)

            if action_schema:
                _validate_action(action_schema, result, output_key)

    except jsonschema.ValidationError:
        LOG.exception("Failed to validate output.")
        _, ex, _ = sys.exc_info()
        # mark execution as failed.
        status = action_constants.LIVEACTION_STATUS_FAILED
        # include the error message and traceback to try and provide some hints.
        result = {
            "error": str(ex),
            "message": "Error validating output. See error output for more details.",
        }
        return (result, status)
    except:
        LOG.exception("Failed to validate output.")
        _, ex, tb = sys.exc_info()
        # mark execution as failed.
        status = action_constants.LIVEACTION_STATUS_FAILED
        # include the error message and traceback to try and provide some hints.
        result = {
            "traceback": "".join(traceback.format_tb(tb, 20)),
            "error": str(ex),
            "message": "Error validating output. See error output for more details.",
        }
        return (result, status)

    return (result, status)
