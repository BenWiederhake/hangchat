#!/bin/false
# This is a library.

"""
Here's what an interaction with hangchat can look like:

>>> import hangchat
>>> gf = hangchat.GameFactory(['ahoy', 'hell', 'cool', 'cody'])
>>> g = gf.start(None, hangchat.PrintCallbacks(), ['Anton', 'Berta'])
game_started <hangchat.GameState object at 0x7f5117a5fe50>
send_private_hint <hangchat.GameState object at 0x7f5117a5fe50> Anton _o__
send_private_hint <hangchat.GameState object at 0x7f5117a5fe50> Berta __o_
send_public_hint <hangchat.GameState object at 0x7f5117a5fe50> ____
set_timer <hangchat.GameState object at 0x7f5117a5fe50> 30000 None -> 1
>>> g.call_guess('Anton', 'goop')
remove_timer <hangchat.GameState object at 0x7f5117a5fe50> 1
send_sorry_wrong <hangchat.GameState object at 0x7f5117a5fe50> Anton goop
set_timer <hangchat.GameState object at 0x7f5117a5fe50> 30000 None -> 2
>>> g.run_timer(None, 2)
send_public_hint <hangchat.GameState object at 0x7f5117a5fe50> ___l
set_timer <hangchat.GameState object at 0x7f5117a5fe50> 30000 None -> 3
>>> g.call_guess('Berta', 'cool')
remove_timer <hangchat.GameState object at 0x7f5117a5fe50> 3
game_ended <hangchat.GameState object at 0x7f5117a5fe50> cool Berta None
>>> g = gf.start(None, hangchat.PrintCallbacks(), ['Anton', 'Berta'])
game_started <hangchat.GameState object at 0x7f5117874c10>
send_private_hint <hangchat.GameState object at 0x7f5117874c10> Anton h___
send_private_hint <hangchat.GameState object at 0x7f5117874c10> Berta __l_
send_public_hint <hangchat.GameState object at 0x7f5117874c10> ____
set_timer <hangchat.GameState object at 0x7f5117874c10> 30000 None -> 1
>>> g.run_timer(None, 1)
send_public_hint <hangchat.GameState object at 0x7f5117874c10> ___l
set_timer <hangchat.GameState object at 0x7f5117874c10> 30000 None -> 2
>>> g.run_timer(None, 2)
send_public_hint <hangchat.GameState object at 0x7f5117874c10> _e_l
set_timer <hangchat.GameState object at 0x7f5117874c10> 30000 None -> 3
>>> g.run_timer(None, 3)
send_public_hint <hangchat.GameState object at 0x7f5117874c10> _ell
set_timer <hangchat.GameState object at 0x7f5117874c10> 30000 None -> 4
>>> g.run_timer(None, 4)
game_ended <hangchat.GameState object at 0x7f5117874c10> hell None None
>>>

Note that the caller manages the timer, so that makes mocking / single-threading easier.
"""

import secrets


# === Interface ===

class AbstractCallbacks:
    """
    Represents the outgoing part of the API, as seen from the backend.
    See `GameFactory.start()` for more details on `game_id`.
    """

    def game_started(self, game_id):
        raise NotImplementedError()

    def send_private_hint(self, game_id, player, hint):
        raise NotImplementedError()

    def send_sorry_wrong(self, game_id, player, wrong_word):
        raise NotImplementedError()

    def send_public_hint(self, game_id, hint):
        raise NotImplementedError()

    def game_ended(self, game_id, word, winner_or_none, slacker_or_none):
        raise NotImplementedError()

    def set_timer(self, game_id, milliseconds, action_data):
        """
        Returns a timer_id (string, int, anything that can be a hashed).
        """
        raise NotImplementedError()

    def remove_timer(self, game_id, timer_id):
        raise NotImplementedError()


class DummyCallbacks(AbstractCallbacks):
    """
    Dummy implementation.  Does nothing, successfully.
    """

    def __init__(self):
        self.counter = 0

    def game_started(self, game_id):
        pass

    def send_private_hint(self, game_id, player, hint):
        pass

    def send_sorry_wrong(self, game_id, player, wrong_word):
        pass

    def send_public_hint(self, game_id, hint):
        pass

    def game_ended(self, game_id, word, winner_or_none, slacker_or_none):
        pass

    def set_timer(self, game_id, milliseconds, action_data):
        # Maybe in the future I actually need more than one timer.
        # Therefore, the dummy needs to guarantee unique IDs.
        self.counter += 1
        return self.counter

    def remove_timer(self, game_id, timer_id):
        pass


class PrintCallbacks(AbstractCallbacks):
    """
    'Print' implementation.  Talks all day long, but does nothing.
    Alternative name: `PoliticianCallbacks`.
    """

    def __init__(self):
        self.counter = 0

    def game_started(self, game_id):
        print('game_started', game_id)

    def send_private_hint(self, game_id, player, hint):
        print('send_private_hint', game_id, player, hint)

    def send_sorry_wrong(self, game_id, player, wrong_word):
        print('send_sorry_wrong', game_id, player, wrong_word)

    def send_public_hint(self, game_id, hint):
        print('send_public_hint', game_id, hint)

    def game_ended(self, game_id, word, winner_or_none, slacker_or_none):
        print('game_ended', game_id, word, winner_or_none, slacker_or_none)

    def set_timer(self, game_id, milliseconds, action_data):
        # Maybe in the future I actually need more than one timer.
        # Therefore, the dummy needs to guarantee unique IDs.
        self.counter += 1
        print('set_timer', game_id, milliseconds, action_data, '->', self.counter)
        return self.counter

    def remove_timer(self, game_id, timer_id):
        print('remove_timer', game_id, timer_id)


# === Magic numbers ===

# See `GameFactory.set_default_timeout_ms` and `GameState.set_timeout_ms`.
DEFAULT_TIMEOUT_MS = 30_000
STATE_UNREVEALED = 0
STATE_PRIVATE_REVEALED = 1
STATE_PUBLIC_REVEALED = 2


# === Helpers ===

def clean_word(word):
    return word.strip().lower()


def read_cleaned_dict(filename):
    with open(dict_file, 'r') as fp:
        # If opening or reading fails, there is nothing meaningful we can do anyway.
        return [clean_word(line) for line in fp.readlines()]


# === Actual implementation ===

class GameFactory:
    """
    Contains all the options and preferences to start a new game, like the dictionary.
    """

    def __init__(self, word_list):
        self.timeout_ms = DEFAULT_TIMEOUT_MS
        self.word_list = None
        self.set_wordlist(word_list)

    def set_wordlist(self, word_list):
        self.word_list = [clean_word(w) for w in word_list]

    def set_default_timeout_ms(self, timeout_ms):
        """
        Only affects new games.
        See also: `GameState.set_timeout_ms()`
        """
        self.timeout_ms = timeout_ms

    def start(self, game_id, callbacks, players):
        """
        game_id: arbitrary, will be passed back to `callbacks`.  If `None`, will use to the `GameState` object.
        callbacks: instance of `AbstractCallbacks`.
        players: list of non-equal numbers or strings (mixed) that `callbacks` understands.
        """
        # TODO: Do something more sophisticated here; maybe avoid picking the same word too often?
        # Maybe something like https://github.com/BenWiederhake/random_tweets/blob/master/feel_random.py
        word = secrets.choice(self.word_list)
        return GameState(game_id, callbacks, players, word, self.timeout_ms)


class GameState:
    """
    Represents a running game.
    """

    def __init__(self, game_id, callbacks, players, word, timeout_ms):
        """
        game_id: arbitrary, will be passed back to `callbacks`.
        callbacks: instance of `AbstractCallbacks`.
        players: list of non-equal numbers or strings (mixed) that `callbacks` understands.
        """
        # Basic setup
        self.game_id = game_id
        if self.game_id is None:
            self.game_id = self
        self.callbacks = callbacks
        self.player_guesses = {p: 0 for p in players}
        # This can fail if a player occurs twice, two players have an equal
        # (`==`) ID, or you supplied a generator instead of a sequence.
        assert len(self.player_guesses) == len(players), (self.player_guesses, players)
        self.word = word
        self.timeout_ms = timeout_ms
        self.hint_states = [STATE_UNREVEALED] * len(word)
        self.is_running = True
        self.last_timer = None

        callbacks.game_started(self.game_id)
        self._send_first_hints()
        self._set_timer()

    def set_timeout_ms(self, timeout_ms):
        """
        timeout_ms: The new timeout amount in milliseconds.

        Note that this does *not* affect the currently running timeout. This
        would require monotonic time: `set_timeout_ms` would first need to
        determine how much time of the currently running timer has passed,
        cancel that timer, and restart it with an appropriate calculated
        amount.

        In short, this would be very non-trivial, so fuck it.
        """
        self.timeout_ms = timeout_ms

    def call_abort_game(self):
        """
        A user or something requested the game to be aborted.
        This method performs cleanup, specifically calls `remove_timer`
        and `game_ended` if appliccable.
        Note that a `GameState` instance can also be just dropped, if you prefer that.
        """
        assert self.is_running
        self.is_running = False
        self._clear_timer()
        self.callbacks.game_ended(self.game_id, self.word, None, self._determine_slacker())

    def call_repeat_public_hint(self):
        """
        Repeats the last public hint, and resets the timeout.
        """
        assert self.is_running
        # Clear the timer beforehand, to avoid accidents.
        self._clear_timer()

        revealed_indices = {i for i, state in enumerate(self.hint_states) if state == STATE_PUBLIC_REVEALED}
        hint_string = self._make_hint(revealed_indices)
        self.callbacks.send_public_hint(self.game_id, hint_string)

        self._set_timer()

    def call_guess(self, player, guessed_word):
        """
        player: The player making the guess.
        guessed_word: The guessed word.  Duh.
        """
        assert self.is_running
        assert player in self.player_guesses, (player, self.player_guesses)
        # Clear the timer beforehand, to avoid accidents.
        self._clear_timer()
        self.player_guesses[player] += 1

        guessed_word = clean_word(guessed_word)
        # If we ever get excesively serious about this, here's an opportunity for timing attacks:
        if guessed_word == self.word:
            self.is_running = False
            self.callbacks.game_ended(self.game_id, self.word, player, self._determine_slacker())
        else:
            self.callbacks.send_sorry_wrong(self.game_id, player, guessed_word)
            self._set_timer()

    def run_timer(self, action_data, timer_id):
        """
        action_data: The piece of data given to `AbstractCallbacks.set_timer` earlier.
        timer_id: The ID of the timer associated with the current call. Note that it
            is no longer valid, and a new call to `set_timer` may return the same ID again.
        """
        assert self.is_running
        assert action_data is None, action_data  # `action_data` is not used yet.
        assert self.last_timer is not None
        assert self.last_timer == timer_id, (self.last_timer, timer_id)
        self.last_timer = None

        hint_index = self._pick_hint_index()
        self.hint_states[hint_index] = STATE_PUBLIC_REVEALED
        revealed_indices = {i for i, state in enumerate(self.hint_states) if state == STATE_PUBLIC_REVEALED}
        if len(revealed_indices) >= len(self.word):
            # We're about to reveal the entire word.
            # This means the players have totally and utterly failed.
            # So instead of revealing the last letter, instead we end the game.
            self.is_running = False
            self.callbacks.game_ended(self.game_id, self.word, None, self._determine_slacker())
            # Don't set a new timer.
            return

        hint_string = self._make_hint(revealed_indices)
        self.callbacks.send_public_hint(self.game_id, hint_string)

        self._set_timer()

    def _pick_hint_index(self):
        """
        Picks an arbitrary position that shall be revealed.
        It uses a sophisticated heuristic that employs machine-learning and neural nets.
        (I.e., if-statements and guesstimates from my brain.)

        It is the caller's duty to update `self.hint_states`.
        """
        # Determine the minimum 'reveal' level:
        min_state = min(self.hint_states)
        relevant_indices = [i for (i, state) in enumerate(self.hint_states) if state == min_state]
        assert len(relevant_indices) > 0, (self.hint_states, min_state)

        return secrets.choice(relevant_indices)

    def _make_hint(self, revealed_indices):
        hint_chars = []
        # Not very efficient, but thankfully words aren't that long anyway.
        for i, c in enumerate(self.word):
            if i in revealed_indices:
                hint_chars.append(c)
            else:
                hint_chars.append('_')
        hint_string = ''.join(hint_chars)
        assert len(hint_string) == len(self.word), (self.word, revealed_indices, hint_string)
        return hint_string

    def _send_first_hints(self):
        for player in self.player_guesses.keys():
            hint_index = self._pick_hint_index()
            self.hint_states[hint_index] = STATE_PRIVATE_REVEALED
            hint_string = self._make_hint({hint_index})
            self.callbacks.send_private_hint(self.game_id, player, hint_string)
        self.callbacks.send_public_hint(self.game_id, self._make_hint(set()))

    def _clear_timer(self):
        """
        Internal method to clear all timers.
        """
        if self.last_timer is not None:
            self.callbacks.remove_timer(self.game_id, self.last_timer)
            self.last_timer = None

    def _set_timer(self):
        """
        Internal method to set all timers.
        ("All" is 1.)
        """
        assert self.is_running
        self._clear_timer()
        # Currently, `action_data` isn't used.
        self.last_timer = self.callbacks.set_timer(self.game_id, self.timeout_ms, None)

    def _determine_slacker(self):
        # FIXME: Determine 'slacker'?
        return None
