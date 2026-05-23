import numpy as np


class HumanLikeNeuron:

    def __init__(self):

        self.brain_experience = np.random.rand()

        self.learning_rate = 0.1

    def think(self, inputs):

        return inputs * self.brain_experience

    def learn_from_mistake(
        self,
        inputs,
        correct_answer,
        wrong_prediction
    ):

        error = correct_answer - wrong_prediction

        self.brain_experience += (
            self.learning_rate
            * error
            * inputs
        )

        return error


neuron = HumanLikeNeuron()


def train_brain():

    target_logic = 5

    results = []

    for attempt in range(1, 6):

        guess = neuron.think(1)

        results.append(
            f"Attempt {attempt}: {guess:.4f}"
        )

        if abs(target_logic - guess) > 0.01:

            error = neuron.learn_from_mistake(
                1,
                target_logic,
                guess
            )

            results.append(
                f"Error: {error:.4f}"
            )

        else:

            results.append(
                "Brain learned successfully."
            )

            break

    return "\n".join(results)
