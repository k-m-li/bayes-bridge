import numpy as np
import scipy.sparse as sparse
from .abstract_matrix import AbstractDesignMatrix
from .mkl_matvec import mkl_csr_matvec


class SparseDesignMatrix(AbstractDesignMatrix):

    def __init__(self, X, use_mkl=True, center_predictor=False, add_intercept=True,
                 copy_array=False, dot_format='csr', Tdot_format='csr'):
        """
        Params:
        ------
        X : scipy sparse matrix
        """
        if copy_array:
            X = X.copy()
        super().__init__(X)
        if dot_format == 'csc' or Tdot_format == 'csc':
            raise NotImplementedError(
                "Current dot operations are only implemented for the CSR format."
            )

        self.use_mkl = use_mkl

        self.centered = center_predictor
        if center_predictor:
            self.column_offset = np.squeeze(np.array(X.mean(axis=0)))
        else:
            self.column_offset = np.zeros(X.shape[1])

        self.intercept_added = add_intercept
        self.X_csr = X.tocsr()

    @property
    def shape(self):
        shape = self.X_csr.shape
        return shape[0], shape[1] + int(self.intercept_added)

    def dot(self, v):

        if self.memoized and np.all(self.v_prev == v):
            return self.X_dot_v

        intercept_effect = 0.
        if self.intercept_added:
            intercept_effect += v[0]
            v = v[1:]
        result = intercept_effect + self.main_dot(v)
        
        if self.memoized:
            self.X_dot_v = result
            self.v_prev = v
        self.dot_count += 1

        return result

    def main_dot(self, v):
        """ Multiply by the main effect part of the design matrix. """
        X = self.X_csr
        result = mkl_csr_matvec(X, v) if self.use_mkl else X.dot(v)
        result -= np.inner(self.column_offset, v)
        if self.memoized:
            self.X_dot_v = result
        return result

    def Tdot(self, v):
        result = self.main_Tdot(v)
        if self.intercept_added:
            result = np.concatenate(([np.sum(v)], result))
        self.Tdot_count += 1
        return result

    def main_Tdot(self, v):
        X = self.X_csr
        result = mkl_csr_matvec(X, v, transpose=True) \
            if self.use_mkl else X.T.dot(v)
        result -= np.sum(v) * self.column_offset
        return result

    def compute_fisher_info(self, weight, diag_only=False):
        """ Compute $X^T W X$ where W is the diagonal matrix of a given weight."""

        if diag_only:
            return self.compute_fisher_diag(weight)

        weight_mat = self.create_diag_matrix(weight)
        X_csr = self.X_csr
        X_T = X_csr.T
        weighted_X = weight_mat.dot(X_csr).tocsc()

        n_pred = self.shape[1]
        fisher_info = np.zeros((n_pred, n_pred))
        if self.intercept_added:
            fisher_info[0, 0] = np.sum(weight)
            fisher_info[0, 1:] \
                = weighted_X.sum(0) - np.sum(weight) * self.column_offset
            fisher_info[1:, 0] = fisher_info[0, 1:]
            fisher_info_wo_intercept = fisher_info[1:, 1:]
        else:
            fisher_info_wo_intercept = fisher_info

        fisher_info_wo_intercept += X_T.dot(weighted_X).toarray()
        if self.centered:
            outer_prod_term = np.outer(
                self.column_offset, weighted_X.sum(0)
            )
            fisher_info_wo_intercept -= outer_prod_term + outer_prod_term.T
            fisher_info_wo_intercept \
                += np.sum(weight) * np.outer(self.column_offset, self.column_offset)

        return fisher_info

    def compute_fisher_diag(self, weight):

        weight_mat = self.create_diag_matrix(weight)
        diag = weight_mat.dot(self.X_csr.power(2)).sum(0)
        if self.centered:
            weighted_X = weight_mat.dot(self.X_csr).tocsc()
            diag -= 2 * self.column_offset \
                    * np.squeeze(np.asarray(weighted_X.sum(0)))
            diag += np.sum(weight) * self.column_offset ** 2
        diag = np.squeeze(np.asarray(diag))
        if self.intercept_added:
            diag = np.concatenate(([np.sum(weight)], diag))

        return diag

    def create_diag_matrix(self, v):
        return sparse.dia_matrix((v, 0), (len(v), len(v)))

    def toarray(self):
        return self.X_csr.toarray() - self.column_offset[np.newaxis, :]

    def extract_matrix(self, order=None):
        pass