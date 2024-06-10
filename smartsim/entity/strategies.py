# BSD 2-Clause License
#
# Copyright (c) 2021-2024, Hewlett Packard Enterprise
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Generation Strategies

from __future__ import annotations

import functools
import itertools
import random
import typing as t

from smartsim.error import errors

TPermutationStrategy = t.Callable[
    [t.Mapping[str, t.Sequence[str]], int], list[dict[str, str]]
]
_REGISTERED_STRATEGIES: t.Final[dict[str, TPermutationStrategy]] = {}

def _register_permutations(name: str) -> t.Callable[
    [TPermutationStrategy],
    TPermutationStrategy,
]:
    def _impl(fn: TPermutationStrategy) -> TPermutationStrategy:
        if name in _REGISTERED_STRATEGIES:
            msg = f"A strategy with the name '{name}' has already been registered"
            raise ValueError(msg)
        _REGISTERED_STRATEGIES[name] = fn
        print(f"here: {_REGISTERED_STRATEGIES}")
        return fn

    return _impl

def resolve(strategy: str | TPermutationStrategy) -> TPermutationStrategy:
    if callable(strategy):
        return _make_safe_custom_strategy(strategy)
    try:
        return _REGISTERED_STRATEGIES[strategy]
    except KeyError:
        raise ValueError(
            f"Failed to find an ensembling strategy by the name of '{strategy}'."
            f"All known strategies are:\n{', '.join(_REGISTERED_STRATEGIES)}"
        ) from None

def _make_safe_custom_strategy(fn: TPermutationStrategy) -> TPermutationStrategy:
    @functools.wraps(fn)
    def _impl(
        params: t.Mapping[str, t.Sequence[str]], n_permutations: int
    ) -> list[dict[str, str]]:
        try:
            permutations = fn(params, n_permutations)
        except Exception as e:
            raise errors.UserStrategyError(str(fn)) from e
        if not isinstance(permutations, list) or not all(
            isinstance(permutation, dict) for permutation in permutations
        ):
            raise errors.UserStrategyError(str(fn))
        return permutations

    return _impl

# create permutations of all parameters
# single application if parameters only have one value
@_register_permutations("all_perm")
def create_all_permutations( # Instead return the class
    params: t.Mapping[str, t.Sequence[str]],
    _n_permutations: int = 0,
    # ^^^^^^^^^^^^^
    # TODO: Really don't like that this attr is ignored, but going to leave it
    #       as the original impl for now. Will change if requested!
) -> list[dict[str, str]]:
    permutations = itertools.product(*params.values())
    return [dict(zip(params, permutation)) for permutation in permutations][:_n_permutations]


@_register_permutations("step")
def step_values(
    params: t.Mapping[str, t.Sequence[str]], _n_permutations: int = 0
) -> list[dict[str, str]]:
    steps = zip(*params.values())
    return [dict(zip(params, step)) for step in steps][:_n_permutations]


@_register_permutations("random")
def random_permutations(
    params: t.Mapping[str, t.Sequence[str]], n_permutations: int = 0
) -> list[dict[str, str]]:
    permutations = create_all_permutations(params, n_permutations)

    # sample from available permutations if n_permutations is specified
    if 0 < n_permutations < len(permutations):
        permutations = random.sample(permutations, n_permutations)

    return permutations

# A type alias -> a Callable (function) that takes in:
#          1. exe_arg_parameters PERMUTATIONS of type dict[str, list[str]]]
#          2. parameters PERMUTATIONS of type list[dict[str, str]]
# and it will return:
#          - type: list[tuple[dict[str, str], dict[str, list[str]]]]
#          - example: [({'EXE': ['a'], 'ARGS': ['e', 'f']}, {'SPAM': 'a', 'EGGS': 'd'})]
TCombinationStrategy = t.Callable[
    [list[dict[str, str]], list[dict[str, str]]], list[tuple[dict[str, str], dict[str, list[str]]]]
]

# Defined a dictionary variable that will store:
#          {  
#             'all_perm': <function create_all_combinations>,
#             'step': <function step_combinations>, 
#             'random': <function random_combinations>
#          }
_REGISTERED_COMBINATION_STRATEGIES: t.Final[dict[str, TCombinationStrategy]] = {}

# A decorator function to register combination of sequence functions
# Called when @_register_combinations decorators are reached
def _register_combinations(name: str) -> t.Callable[
    [TCombinationStrategy],
    TCombinationStrategy,
]:
    def _impl(fn: TPermutationStrategy) -> TPermutationStrategy:
        if name in _REGISTERED_COMBINATION_STRATEGIES:
            msg = f"A combination strategy with the name '{name}' has already been registered"
            raise ValueError(msg)
        _REGISTERED_COMBINATION_STRATEGIES[name] = fn
        return fn

    return _impl

def resolve_combination(strategy: str | TCombinationStrategy) -> TCombinationStrategy:
    return _REGISTERED_COMBINATION_STRATEGIES[strategy]

# Feedback
# Define some classes that make it easier to accomplish in a single method
# Currenlty passing around lots of types, might be helpful to establish order
# Ex: define param set = param with all possible values

# Create something similar to a typedef for return types
# No user facing classes
# Combine into one method


@_register_combinations("all_perm")
def create_all_combinations(
    file_param_permutations,
    exe_arg_permutations,
    _n_permutations,
) -> list[tuple[dict[str, str], dict[str, list[str]]]]:
    if exe_arg_permutations == [{}] and file_param_permutations == [{}]:
        return [({}, {})]
    # Find all possible combinations of file_params and exe_args
    combinations = itertools.product(exe_arg_permutations, file_param_permutations)
    # pg = (next(combinations) for _ in range(_n_permutations))
    result = []
    for _ in range(_n_permutations):
        try:
            val = next(combinations)
            print(f"yurp: {val}")
            result.append(val)
        except StopIteration:
            break
    print(f"length: {len(result)}")
    return result

@_register_combinations("step")
def step_combinations(
    file_param_permutations,
    exe_arg_permutations,
    _n_permutations,
) -> list[tuple[dict[str, str], dict[str, list[str]]]]:
    combinations = []
    if exe_arg_permutations == [{}]:
        # Unzip the values from the input dictionaries
        for f in zip(file_param_permutations):
            # Append the tuple to the result list
            combinations.append((f, {}))
            if len(combinations) >= _n_permutations:
                break
    else:
        # Unzip the values from the input dictionaries
        for (f, b) in zip(file_param_permutations, exe_arg_permutations):
            # Append the tuple to the result list
            combinations.append((f, b))
            if len(combinations) >= _n_permutations:
                break
    return combinations

@_register_combinations("random")
def random_combinations(
    file_param_permutations,
    exe_arg_permutations,
    _n_permutations,
) -> list[tuple[dict[str, str], dict[str, list[str]]]]:
    combinations = create_all_combinations(file_param_permutations, exe_arg_permutations, _n_permutations)

    # sample from available permutations if n_permutations is specified
    if 0 < _n_permutations < len(combinations):
        combinations = random.sample(combinations, _n_permutations)
    return combinations