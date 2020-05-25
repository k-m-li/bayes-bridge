from warnings import warn
import scipy as sp

from .linear_model import LinearModel
from .logistic_model import LogisticModel
from .cox_model import CoxModel
from ..design_matrix import DenseDesignMatrix, SparseDesignMatrix

def RegressionModel(
        outcome, X, model_type='linear',
        add_intercept=None, center_predictor=False
    ):
    """
    Params
    ------
    outcome : vector if model_type == 'linear' else tuple
        (n_success, n_trial) if model_type == 'logistic'.
            The outcome is assumed binary if n_trial is None.
        (event_time, censoring_time) if model_type == 'cox'
    X : numpy array or scipy sparse matrix
    n_trial : vector
        Used for the logistic model_type for binomial outcomes.
    model_type : str, {'linear', 'logit'}
    """

    # TODO: Make each MCMC run more "independent" i.e. not rely on the
    # previous instantiation of the class. The initial run of the Gibbs
    # sampler probably depends too much the stuffs here.

    if add_intercept is None:
        add_intercept = (model_type != 'cox')

    if model_type == 'cox':
        if add_intercept:
            add_intercept = False
            warn("Intercept is not identifiable in Cox model and won't be added.")
        event_time, censoring_time = outcome
        event_time, censoring_time, X = CoxModel.preprocess_data(
            event_time, censoring_time, X
        )

    is_sparse = sp.sparse.issparse(X)
    DesignMatrix = SparseDesignMatrix if is_sparse else DenseDesignMatrix
    design = DesignMatrix(
        X, add_intercept=add_intercept, center_predictor=center_predictor
    )

    if model_type == 'linear':
        model = LinearModel(outcome, design)
    elif model_type == 'logit':
        n_success, n_trial = outcome
        model = LogisticModel(n_success, n_trial, design)
    elif model_type == 'cox':
        model = CoxModel(event_time, censoring_time, design)
    else:
        raise NotImplementedError()

    return model