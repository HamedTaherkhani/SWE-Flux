import numpy as np

from keras.src import losses
from keras.src import testing


class LossesStateLoopQATest(testing.TestCase):
    def test_running_weighted_sum_after_while_loop(self):
        y_true_steps = [
            np.array([[1.0, 0.0, 1.0, 0.0]], dtype="float32"),
            np.array([[0.0, 1.0, 0.0, 1.0]], dtype="float32"),
            np.array([[1.0, 1.0, 0.0, 0.0]], dtype="float32"),
        ]
        y_pred_logits_steps = [
            np.array([[2.2, -1.2, 0.9, -0.8]], dtype="float32"),
            np.array([[-0.7, 1.8, -1.1, 1.3]], dtype="float32"),
            np.array([[1.4, 0.6, -0.9, -1.6]], dtype="float32"),
        ]

        step = 0
        running_weighted_sum = 0.0
        per_step_loss_means = []

        while step < len(y_true_steps):
            current_label_smoothing = 0.1 if step != 1 else 0.2
            loss_vector = losses.binary_focal_crossentropy(
                y_true=y_true_steps[step],
                y_pred=y_pred_logits_steps[step],
                apply_class_balancing=True,
                alpha=0.3,
                gamma=2.5,
                from_logits=True,
                label_smoothing=current_label_smoothing,
                axis=-1,
            )
            loss_mean = float(np.mean(np.array(loss_vector)))
            per_step_loss_means.append(loss_mean)
            running_weighted_sum += (step + 1) * loss_mean
            if step == 1 and running_weighted_sum > 0.2:
                running_weighted_sum -= 0.05
            step += 1

        self.assertGreater(running_weighted_sum, 0.0)
