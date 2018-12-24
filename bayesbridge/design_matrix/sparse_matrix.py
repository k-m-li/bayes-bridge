import numpy as np
import scipy.sparse as sparse
from .abstract_matrix import AbstractDesignMatrix

class SparseDesignMatrix(AbstractDesignMatrix):

    def __init__(self, X):
        """
        Params:
        ------
        X : scipy sparse matrix
        """
        super().__init__(X)
        self.X_row_major = X.tocsr()
        self.X_col_major = X.tocsc()

    def dot(self, v):
        same_input = False
        if self.memoized:
            same_input = np.all(self.v_prev == v)
            if same_input:
                result = self.X_dot_v
            else:
                result = self.X_row_major.dot(v)
                self.X_dot_v = result
            self.v_prev = v
        else:
            result = self.X_row_major.dot(v)
        super().dot(None, same_input)
        return result

    def Tdot(self, v):
        super().Tdot(None)
        return self.X_col_major.T.dot(v)

    def compute_fisher_info(self, weight, diag_only=False):

        weight_mat = self.create_diag_matrix(weight)

        if diag_only:
            diag = weight_mat.dot(self.X_row_major.power(2)).sum(0)
            return np.squeeze(np.asarray(diag))
        else:
            X_T = self.X_row_major.T
            weighted_X = weight_mat.dot(self.X_row_major).tocsc()
            return X_T.dot(weighted_X).toarray()

    def create_diag_matrix(self, v):
        return sparse.dia_matrix((v, 0), (len(v), len(v)))

    def toarray(self):
        return self.X_row_major.toarray()

    def extract_matrix(self, order=None):
        pass