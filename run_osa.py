import os
import time
import optuna
import logging
import sys
from run_config import *
from streamline.dataprep.eda_runner import EDARunner
from streamline.dataprep.data_process import DataProcessRunner
from streamline.featurefns.feature_runner import FeatureImportanceRunner
from streamline.featurefns.feature_runner import FeatureSelectionRunner
from streamline.modeling.model_runner import ModelExperimentRunner
from streamline.postanalysis.stats_runner import StatsRunner
from streamline.postanalysis.compare_runner import CompareRunner
from streamline.postanalysis.report_runner import ReportRunner
optuna.logging.set_verbosity(optuna.logging.WARNING)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

# stdout_handler = logging.StreamHandler(sys.stdout)
# stdout_handler.setLevel(logging.DEBUG)
# stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)


def run(obj, phase_str, run_parallel=True):
    start = time.time()
    obj.run(run_parallel=run_parallel)
    print("Ran " + phase_str + " Phase in " + str(time.time() - start))
    del obj


if __name__ == "__main__":

    start_g = time.time()

    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH)

    eda = EDARunner(DATASET_PATH, OUTPUT_PATH, EXPERIMENT_NAME,
                    class_label=CLASS_LABEL, instance_label=INSTANCE_LABEL, random_state=42)
    run(eda, "Exploratory")

    dpr = DataProcessRunner(OUTPUT_PATH, EXPERIMENT_NAME,
                            class_label=CLASS_LABEL, instance_label=INSTANCE_LABEL, random_state=42)
    run(dpr, "Data Process")

    f_imp = FeatureImportanceRunner(OUTPUT_PATH, EXPERIMENT_NAME, algorithms=FEATURE_ALGORITHMS,
                                    class_label=CLASS_LABEL, instance_label=INSTANCE_LABEL, random_state=42)
    run(f_imp, "Feature Imp.")

    f_sel = FeatureSelectionRunner(OUTPUT_PATH, EXPERIMENT_NAME, algorithms=FEATURE_ALGORITHMS,
                                   class_label=CLASS_LABEL, instance_label=INSTANCE_LABEL, random_state=42)
    run(f_sel, "Feature Sel.")

    model = ModelExperimentRunner(OUTPUT_PATH, EXPERIMENT_NAME, algorithms=None, exclude=["XCS", "eLCS"],
                                  class_label=CLASS_LABEL, instance_label=INSTANCE_LABEL, lcs_iterations=500000,
                                  random_state=RANDOM_STATE)
    run(model, "Modelling", True)

    stats = StatsRunner(OUTPUT_PATH, EXPERIMENT_NAME, algorithms=MODEL_ALGORITHMS)
    run(stats, "Stats")

    compare = CompareRunner(OUTPUT_PATH, EXPERIMENT_NAME, algorithms=MODEL_ALGORITHMS)
    run(compare, "Dataset Compare")

    report = ReportRunner(OUTPUT_PATH, EXPERIMENT_NAME, algorithms=MODEL_ALGORITHMS)
    run(report, "Reporting")

    print("DONE!!!")
    print("Ran in " + str(time.time() - start_g))
