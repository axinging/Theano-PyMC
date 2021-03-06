import numpy as np

import theano
import theano.tensor as tt
from tests import unittest_tools as utt
from theano.breakpoint import PdbBreakpoint


class TestPdbBreakpoint(utt.InferShapeTester):
    def setup_method(self):
        super().setup_method()

        # Sample computation that involves tensors with different numbers
        # of dimensions
        self.input1 = tt.fmatrix()
        self.input2 = tt.fscalar()
        self.output = tt.dot(
            (self.input1 - self.input2), (self.input1 - self.input2).transpose()
        )

        # Declare the conditional breakpoint
        self.breakpointOp = PdbBreakpoint("Sum of output too high")
        self.condition = tt.gt(self.output.sum(), 1000)
        (
            self.monitored_input1,
            self.monitored_input2,
            self.monitored_output,
        ) = self.breakpointOp(self.condition, self.input1, self.input2, self.output)

    def test_infer_shape(self):

        input1_value = np.arange(6).reshape(2, 3).astype("float32")
        input2_value = 10.0

        self._compile_and_check(
            [self.input1, self.input2],
            [self.monitored_input1, self.monitored_input2, self.monitored_output],
            [input1_value, input2_value],
            PdbBreakpoint,
        )

    def test_grad(self):

        input1_value = np.arange(9).reshape(3, 3).astype("float32")
        input2_value = 10.0

        grads = [
            tt.grad(self.monitored_input1.sum(), self.input1),
            tt.grad(self.monitored_input2.sum(), self.input2),
        ]

        # Add self.monitored_input1 as an output to the Theano function to
        # prevent Theano from optimizing the PdbBreakpoint op out of the
        # function graph
        fct = theano.function(
            [self.input1, self.input2], grads + [self.monitored_input1]
        )

        gradients = fct(input1_value, input2_value)[:-1]

        expected_gradients = [
            np.ones((3, 3), dtype="float32"),
            np.array(1.0, dtype="float32"),
        ]

        for i in range(len(gradients)):
            np.testing.assert_allclose(gradients[i], expected_gradients[i])

    def test_fprop(self):

        input1_value = np.arange(9).reshape(3, 3).astype("float32")
        input2_value = 10.0
        fct = theano.function(
            [self.input1, self.input2], [self.monitored_input1, self.monitored_input2]
        )

        output = fct(input1_value, input2_value)
        np.testing.assert_allclose(output[0], input1_value)
        np.testing.assert_allclose(output[1], input2_value)

    def test_connection_pattern(self):

        node = self.monitored_output.owner
        connection_pattern = self.breakpointOp.connection_pattern(node)
        expected_pattern = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]

        assert connection_pattern == expected_pattern
