"""
Utility functions to evaluate models on datasets.
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import numpy as np
import warnings
from deepchem.utils.save import log
from sklearn.metrics import mean_squared_error
from sklearn.metrics import roc_auc_score
from sklearn.metrics import r2_score
from sklearn.metrics import matthews_corrcoef
from sklearn.metrics import recall_score
from sklearn.metrics import accuracy_score
import pandas as pd

__author__ = "Bharath Ramsundar"
__copyright__ = "Copyright 2015, Stanford University"
__license__ = "LGPL"

#def undo_normalization(y, y_means, y_stds):
#  """Undo the applied normalization transform."""
#  return y * y_stds + y_means

#def undo_transform(y, y_means, y_stds, output_transforms):
#  """Undo transforms on y_pred, W_pred."""
#  if not isinstance(output_transforms, list):
#    output_transforms = [output_transforms]
#  if (output_transforms == [""]
#      or output_transforms == ['']
#      or output_transforms == []):
#    return y
#  elif output_transforms == ["log"]:
#    return np.exp(y)
#  elif output_transforms == ["normalize"]:
#    return undo_normalization(y, y_means, y_stds)
#  elif output_transforms == ["log", "normalize"]:
#    return np.exp(undo_normalization(y, y_means, y_stds))
#  else:
#    raise ValueError("Unsupported output transforms %s." % str(output_transforms))

def undo_transforms(y, transformers):
  """Undoes all transformations applied."""
  # Note that transformers have to be undone in reversed order
  for transformer in reversed(transformers):
    y = transform.unstranform(y)
  return y

def compute_roc_auc_scores(y, y_pred):
  """Transforms the results dict into roc-auc-scores and prints scores.

  Parameters
  ----------
  results: dict
  task_types: dict
    dict mapping task names to output type. Each output type must be either
    "classification" or "regression".
  """
  try:
    score = roc_auc_score(y, y_pred)
  except ValueError:
    warnings.warn("ROC AUC score calculation failed.")
    score = 0.5
  return score

class Evaluator(object):
  """Class that evaluates a model on a given dataset."""

  def __init__(self, model, dataset, transformers, verbose=False):
    self.model = model
    self.dataset = dataset
    self.transformers = transformers
    self.task_names = dataset.get_task_names()
    # TODO(rbharath): This is a hack based on fact that multi-tasktype models
    # aren't supported.
    self.task_type = model.task_types.itervalues().next()
    self.output_transforms = dataset.get_output_transforms()
    self.verbose = verbose

  def compute_model_performance(self, csv_out, stats_file):
    """
    Computes statistics of model on test data and saves results to csv.
    """
    pred_y_df = self.model.predict(self.dataset)
    log("Saving predictions to %s" % csv_out, self.verbose)
    pred_y_df.to_csv(csv_out)

    if self.task_type == "classification":
      colnames = ["task_name", "roc_auc_score", "matthews_corrcoef",
                  "recall_score", "accuracy_score"]
    elif self.task_type == "regression":
      colnames = ["task_name", "r2_score", "rms_error"]
    else:
      raise ValueError("Unrecognized task type: %s" % self.task_type)

    performance_df = pd.DataFrame(columns=colnames)

    for i, task_name in enumerate(self.task_names):
      y = pred_y_df[task_name].values
      y_pred = pred_y_df["%s_pred" % task_name].values
      w = pred_y_df["%s_weight" % task_name].values
      y = undo_transforms(y)
      y_pred = undo_transform(y_pred)

      if self.task_type == "classification":
        y, y_pred = y[w.nonzero()].astype(int), y_pred[w.nonzero()].astype(int)
        # Sometimes all samples have zero weight. In this case, continue.
        if not len(y):
          continue
        auc = compute_roc_auc_scores(y, y_pred)
        mcc = matthews_corrcoef(y, y_pred)
        recall = recall_score(y, y_pred)
        accuracy = accuracy_score(y, y_pred)
        performance_df.loc[i] = [task_name, auc, mcc, recall, accuracy]

      elif self.task_type == "regression":
        try:
          r2s = r2_score(y, y_pred)
          rms = np.sqrt(mean_squared_error(y, y_pred))
        except ValueError:
          r2s = np.nan
          rms = np.nan
        performance_df.loc[i] = [task_name, r2s, rms]

    log("Saving model performance scores to %s" % stats_file, self.verbose)
    performance_df.to_csv(stats_file)

    return pred_y_df, performance_df
