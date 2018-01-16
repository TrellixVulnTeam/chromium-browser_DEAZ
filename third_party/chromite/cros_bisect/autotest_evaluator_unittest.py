# -*- coding: utf-8 -*-
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test autotest_evaluator module."""

from __future__ import print_function

import os

from chromite.cros_bisect import autotest_evaluator
from chromite.lib import commandline
from chromite.lib import cros_build_lib
from chromite.lib import cros_build_lib_unittest
from chromite.lib import cros_test_lib
from chromite.lib import osutils
from chromite.lib import partial_mock
from chromite.lib import remote_access_unittest


class RemoteShScpMock(remote_access_unittest.RemoteShMock):
  """In addition to RemoteSh, it mocks ScpToLocal."""

  ATTRS = ('RemoteSh', 'ScpToLocal')

  def ScpToLocal(self, _, remote, local):
    return self._results['ScpToLocal'].LookupResult(([remote, local], ))


class TestAutotestEvaluator(cros_test_lib.MockTempDirTestCase):
  """Tests AutotestEvaluator class."""
  BOARD = 'samus'
  TEST_NAME = 'graphics_WebGLAquarium'
  METRIC = 'avg_fps_1000_fishes/summary/value'
  REPORT_FILE = 'reports.json'
  REMOTE_REPORT_FILE = '%s/results/default/%s/results/results-chart.json' % (
      autotest_evaluator.AutotestEvaluator.AUTOTEST_BASE,
      TEST_NAME)
  DUT = commandline.DeviceParser(commandline.DEVICE_SCHEME_SSH)('192.168.1.1')
  TEST_TARGET = '%s/tests/%s/control' % (
      autotest_evaluator.AutotestEvaluator.AUTOTEST_BASE, TEST_NAME)
  AQUARIUM_REPORT_TEMPLATE = """
{"avg_fps_1000_fishes": {
   "summary": {
     "units": "fps",
     "type": "scalar",
     "value": %s,
     "improvement_direction": "up"
    }
  }
}"""
  BUILD_LABEL = 'base'

  def setUp(self):
    self.PatchObject(cros_build_lib, 'IsInsideChroot', return_value=False)

  def GetDefaultEvaluator(self):
    """Gets AutototestEvaluator instance with default options.

    Returns:
      Default AutototestEvaluator instance for test.
    """
    options = cros_test_lib.EasyAttr(
        base_dir=self.tempdir, board=self.BOARD, test_name=self.TEST_NAME,
        metric=self.METRIC, metric_take_average=False, reuse_eval=True,
        chromium_dir=None, cros_dir=None)
    return autotest_evaluator.AutotestEvaluator(options)

  def PrepareWebglAquariumReports(self, scores):
    """Prepares graphics_WebGLAquarium reports.

    It is a simplified version. What test cares is
    "avg_fps_1000_fishes/summary/value". It can produces multiple reports if
    more than one score is given.

    Args:
      scores: List of scores.

    Returns:
      A list of file names storing in report directory.
    """
    result = []
    num_reports = len(scores)
    for ith, score in enumerate(scores, start=1):
      report_file = os.path.join(
          self.tempdir, 'reports',
          'results-chart.%s.%d-%d.json' % (self.BUILD_LABEL, ith, num_reports))
      osutils.WriteFile(report_file, self.AQUARIUM_REPORT_TEMPLATE % score)
      result.append(report_file)
    return result

  def testInit(self):
    """Tests that AutotestEvaluator() works as expected."""
    base_dir = self.tempdir
    evaluator = self.GetDefaultEvaluator()
    self.assertEqual(base_dir, evaluator.base_dir)
    self.assertEqual(os.path.join(base_dir, 'reports'),
                     evaluator.report_base_dir)
    self.assertTrue(os.path.isdir(evaluator.report_base_dir))
    self.assertEqual(self.BOARD, evaluator.board)
    self.assertEqual(self.TEST_NAME, evaluator.test_name)
    self.assertEqual(self.METRIC, evaluator.metric)
    self.assertFalse(evaluator.metric_take_average)
    self.assertTrue(evaluator.reuse_eval)
    self.assertEqual(os.path.join(base_dir, 'chromium'),
                     evaluator.chromium_dir)

    # With chromium_dir specified and flip booleans.
    options = cros_test_lib.EasyAttr(
        base_dir=base_dir, board=self.BOARD, test_name=self.TEST_NAME,
        metric=self.METRIC, metric_take_average=False, reuse_eval=False,
        chromium_dir='/tmp/chromium', cros_dir=None)
    evaluator = autotest_evaluator.AutotestEvaluator(options)
    self.assertFalse(evaluator.metric_take_average)
    self.assertFalse(evaluator.reuse_eval)
    self.assertEqual('/tmp/chromium', evaluator.chromium_dir)

  def testInitMissingRequiredArgs(self):
    """Tests that AE() raises exception when required options are missing."""
    options = cros_test_lib.EasyAttr()
    with self.assertRaises(Exception) as cm:
      autotest_evaluator.AutotestEvaluator(options)
    exception_message = cm.exception.message
    self.assertTrue('Missing command line' in exception_message)
    self.assertTrue('AutotestEvaluator' in exception_message)
    for arg in autotest_evaluator.AutotestEvaluator.REQUIRED_ARGS:
      self.assertTrue(arg in exception_message)

  def testRunTestFromDut(self):
    """Tests that RunTestFromDut() invokes expected commands."""
    evaluator = self.GetDefaultEvaluator()

    rsh_mock = self.StartPatcher(RemoteShScpMock())
    rsh_mock.AddCmdResult(
        [evaluator.AUTOTEST_CLIENT, self.TEST_TARGET], returncode=0)
    rsh_mock.AddCmdResult(
        [self.REMOTE_REPORT_FILE, self.REPORT_FILE], returncode=0,
        mock_attr='ScpToLocal')

    self.assertTrue(evaluator.RunTestFromDut(self.DUT, self.REPORT_FILE))

  def testRunTestFromDutAutotestFail(self):
    """Tests RunTestFromDut() when autotest failed to run remotely."""
    evaluator = self.GetDefaultEvaluator()

    rsh_mock = self.StartPatcher(RemoteShScpMock())
    rsh_mock.AddCmdResult(
        [evaluator.AUTOTEST_CLIENT, self.TEST_TARGET], returncode=1)

    self.assertFalse(evaluator.RunTestFromDut(self.DUT, self.REPORT_FILE))

  def testRunTestFromDutScpReportFail(self):
    """Tests RunTestFromDut() when it failed to remote copy report file."""
    evaluator = self.GetDefaultEvaluator()

    rsh_mock = self.StartPatcher(RemoteShScpMock())
    rsh_mock.AddCmdResult(
        [evaluator.AUTOTEST_CLIENT, self.TEST_TARGET], returncode=0)
    rsh_mock.AddCmdResult(
        [self.REMOTE_REPORT_FILE, self.REPORT_FILE], returncode=1,
        mock_attr='ScpToLocal')

    self.assertFalse(evaluator.RunTestFromDut(self.DUT, self.REPORT_FILE))

  def GetTestResultPath(self, evaluator):
    """Returns base path storing test result.

    Args:
      evaluator: Evaluator object.

    Returns:
      Path where the evaulator stores test results.
    """
    return evaluator.ResolvePathFromChroot(os.path.join(
        '/tmp', 'test_that_latest', 'results-1-%s' % evaluator.test_name))

  def testLookupReportFile(self):
    """Tests LookupReportFile().

    Tests that it invokes expected command and performs path normalization.
    """
    evaluator = self.GetDefaultEvaluator()
    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    results_base_path = self.GetTestResultPath(evaluator)
    find_command_result = (
        './%s/results/results-chart.json\n' % self.TEST_NAME)
    command_mock.AddCmdResult(
        ['find', '.', '-name', 'results-chart.json'],
        kwargs={'cwd': results_base_path, 'capture_output': True},
        output=find_command_result)

    self.assertEqual(
        os.path.join(results_base_path, self.TEST_NAME, 'results',
                     'results-chart.json'),
        evaluator.LookupReportFile())

  def testLookupReportFileMissing(self):
    """Tests LookupReportFile() when the report does not exist."""
    evaluator = self.GetDefaultEvaluator()
    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    results_base_path = self.GetTestResultPath(evaluator)
    command_mock.AddCmdResult(
        ['find', '.', '-name', 'results-chart.json'],
        kwargs={'cwd': results_base_path, 'capture_output': True},
        output='')

    self.assertIsNone(evaluator.LookupReportFile())

  def WriteTestResult(self, evaluator, score=0):
    """Writes a test result to evaluator's default location.

    Args:
      evaluator: Evaluator object.
      score: score of the result.

    Returns:
      (path to test result file, result file's content)
    """
    result_dir = self.GetTestResultPath(evaluator)
    osutils.SafeMakedirs(result_dir)
    result_path = os.path.join(result_dir, evaluator.RESULT_FILENAME)
    result_content = self.AQUARIUM_REPORT_TEMPLATE % score
    osutils.WriteFile(result_path, result_content)
    return (result_path, result_content)

  def testRunTestFromHost(self):
    """Tests TestFromHost().

    Tests that it invokes expected commands and report file being copied to
    designated path.
    """
    evaluator = self.GetDefaultEvaluator()
    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    self.SkipMaySetupBoard(evaluator)
    command_mock.AddCmdResult(
        ['test_that', '-b', self.BOARD, '--fast', '--args', 'local=True',
         '192.168.1.1', self.TEST_NAME], returncode=0)
    report_path, report_content = self.WriteTestResult(evaluator)
    command_mock.AddCmdResult(
        ['find', '.', '-name', 'results-chart.json'],
        output=report_path)

    # Make sure report file is copied to designated path.
    target_report_file = os.path.join(self.tempdir, 'stored-results-chart.json')
    osutils.SafeUnlink(target_report_file)
    self.assertTrue(evaluator.RunTestFromHost(self.DUT, target_report_file))
    self.assertTrue(os.path.exists(target_report_file))
    self.assertEqual(report_content, osutils.ReadFile(target_report_file))

  def testRunTestFromHostTestThatFail(self):
    """Tests TestFromHost() when autotest failed to run."""
    evaluator = self.GetDefaultEvaluator()

    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    self.SkipMaySetupBoard(evaluator)
    command_mock.AddCmdResult(
        ['test_that', '-b', self.BOARD, '--fast', '--args', 'local=True',
         '192.168.1.1', self.TEST_NAME], returncode=1)

    self.assertFalse(evaluator.RunTestFromHost(self.DUT, self.REPORT_FILE))

  def testRunTestFromHostReportFileMissing(self):
    """Tests TestFromHost() when test report file does not exist."""
    evaluator = self.GetDefaultEvaluator()
    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    self.SkipMaySetupBoard(evaluator)
    command_mock.AddCmdResult(
        ['test_that', '-b', self.BOARD, '--fast', '--args', 'local=True',
         '192.168.1.1', self.TEST_NAME], returncode=0)
    command_mock.AddCmdResult(
        ['find', '.', '-name', 'results-chart.json'], output='')

    self.assertFalse(evaluator.RunTestFromHost(self.DUT, self.REPORT_FILE))

  def testGetAutotestMetricValue(self):
    """Tests that GetAutotestMetricValue() extracts score correctly."""
    evaluator = self.GetDefaultEvaluator()
    score = 56.73
    report_file = self.PrepareWebglAquariumReports([score])[0]
    self.assertEqual(score,
                     evaluator.GetAutotestMetricValue(report_file))

  def testGetAutotestMetricValueMetricTakeAverage(self):
    """Tests that GetAutotestMetricValue() extracts averaged scores."""
    # metric_take_average=True
    options = cros_test_lib.EasyAttr(
        base_dir=self.tempdir, board=self.BOARD, test_name=self.TEST_NAME,
        metric=self.METRIC, metric_take_average=True, reuse_eval=True,
        chromium_dir=None, cros_dir=None)
    evaluator = autotest_evaluator.AutotestEvaluator(options)

    scores = [55, 57, 58]
    # A report's value is a list of scores.
    report_file = self.PrepareWebglAquariumReports([scores])[0]
    self.assertAlmostEqual(56.66, evaluator.GetAutotestMetricValue(report_file),
                           delta=0.01)

  def testEvaluateRunTestFromDut(self):
    """Tests Evaluate() which runs test from DUT."""
    evaluator = self.GetDefaultEvaluator()

    # Mock RunTestFromDut success.
    rsh_mock = self.StartPatcher(RemoteShScpMock())
    rsh_mock.AddCmdResult(
        [evaluator.AUTOTEST_CLIENT, self.TEST_TARGET], returncode=0)

    # Prepare result for evaluate.
    score = 56.73
    report_file = self.PrepareWebglAquariumReports([score])[0]

    rsh_mock.AddCmdResult(
        [self.REMOTE_REPORT_FILE, report_file], returncode=0,
        mock_attr='ScpToLocal')

    eval_score = evaluator.Evaluate(self.DUT, self.BUILD_LABEL)
    self.assertEqual(1, len(eval_score.values))
    self.assertEqual(score, eval_score.values[0])
    self.assertEqual(score, eval_score.mean)
    self.assertEqual(0.0, eval_score.variance)
    self.assertEqual(0.0, eval_score.std)

  def testEvaluateTwiceRunTestFromDut(self):
    """Tests Evaluate() with repeat=2 which runs test from DUT."""
    evaluator = self.GetDefaultEvaluator()

    # Mock RunTestFromDut success.
    rsh_mock = self.StartPatcher(RemoteShScpMock())
    rsh_mock.AddCmdResult(
        [evaluator.AUTOTEST_CLIENT, self.TEST_TARGET], returncode=0)

    # Prepare two results for evaluate.
    scores = [56, 58]
    report_files = self.PrepareWebglAquariumReports(scores)

    for report_file in report_files:
      rsh_mock.AddCmdResult(
          [self.REMOTE_REPORT_FILE, report_file], returncode=0,
          mock_attr='ScpToLocal')

    eval_score = evaluator.Evaluate(self.DUT, self.BUILD_LABEL, repeat=2)
    self.assertEqual(2, len(eval_score.values))
    self.assertEqual(scores[0], eval_score.values[0])
    self.assertEqual(scores[1], eval_score.values[1])
    self.assertEqual(57, eval_score.mean)
    self.assertEqual(2.0, eval_score.variance)
    self.assertAlmostEqual(1.414, eval_score.std, delta=0.01)

  def SkipMaySetupBoard(self, evaluator):
    """Let evaluator.MaySetupBoard() returns True without action.

    It touches /build/{board} directory inside chroot so that MaySetupBoard()
    thinks the board is already set up.
    """
    osutils.SafeMakedirs(os.path.join(evaluator.cros_dir, 'chroot', 'build',
                                      evaluator.board))

  def testEvaluateFromHost(self):
    """Tests Evaluate() which runs test from host."""
    evaluator = self.GetDefaultEvaluator()

    # Mock RunTestFromDut fail.
    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    command_mock.AddCmdResult(
        partial_mock.InOrder([evaluator.AUTOTEST_CLIENT, self.TEST_TARGET]),
        returncode=1)

    self.SkipMaySetupBoard(evaluator)

    # Mock RunTestFromHost success.
    command_mock.AddCmdResult(
        ['test_that', '-b', self.BOARD, '--fast', '--args', 'local=True',
         '192.168.1.1', self.TEST_NAME], returncode=0)

    # Mock 'find' and returns a result file for verify.
    score = 59.9
    report_file_in_chroot, _ = self.WriteTestResult(evaluator, score)
    command_mock.AddCmdResult(
        ['find', '.', '-name', 'results-chart.json'],
        output=report_file_in_chroot)

    eval_score = evaluator.Evaluate(self.DUT, self.BUILD_LABEL)
    self.assertEqual(1, len(eval_score.values))
    self.assertEqual(score, eval_score.values[0])
    self.assertEqual(score, eval_score.mean)
    self.assertEqual(0.0, eval_score.variance)
    self.assertEqual(0.0, eval_score.std)

  def testCheckLastEvaluate(self):
    """Tests CheckLastEvaluate().

    Test that it extracts score from last evaluation result.
    """
    evaluator = self.GetDefaultEvaluator()

    scores = [56, 58]
    self.PrepareWebglAquariumReports(scores)

    eval_score = evaluator.CheckLastEvaluate(self.BUILD_LABEL, repeat=2)
    self.assertEqual(2, len(eval_score.values))
    self.assertEqual(scores[0], eval_score.values[0])
    self.assertEqual(scores[1], eval_score.values[1])
    self.assertEqual(57, eval_score.mean)
    self.assertEqual(2.0, eval_score.variance)
    self.assertAlmostEqual(1.414, eval_score.std, delta=0.01)

  def testCheckLastEvaluateDifferentLabel(self):
    """Tests that CheckLastEvaluate() failed to extracts score."""
    evaluator = self.GetDefaultEvaluator()

    scores = [56, 58]
    self.PrepareWebglAquariumReports(scores)

    eval_score = evaluator.CheckLastEvaluate('different_build', repeat=2)
    self.assertEqual(0, len(eval_score))

  def testCheckLastEvaluateFlagUnset(self):
    """Tests CheckLastEvaluate() when "reuse_eval" option is unset.

    Tests that it always returns empty score when "reuse_eval" option is unset.
    """
    # 'reuse_eval' set to False.
    options = cros_test_lib.EasyAttr(
        base_dir=self.tempdir, board=self.BOARD, test_name=self.TEST_NAME,
        metric=self.METRIC, metric_take_average=False, reuse_eval=False,
        chromium_dir=None, cros_dir=None)
    evaluator = autotest_evaluator.AutotestEvaluator(options)

    scores = [56, 58]
    self.PrepareWebglAquariumReports(scores)

    eval_score = evaluator.CheckLastEvaluate(self.BUILD_LABEL, repeat=2)
    self.assertEqual(0, len(eval_score))

  def CreateCommandMockForRepo(self, cwd):
    """Creates a command mock and add commands "repo init" "repo sync".

    Args:
      cwd: Directory for running "repo init".

    Returns:
      command_mock object.
    """
    command_mock = self.StartPatcher(cros_build_lib_unittest.RunCommandMock())
    command_mock.AddCmdResult(
        ['repo', 'init', '-u',
         'https://chromium.googlesource.com/chromiumos/manifest.git',
         '--repo-url',
         'https://chromium.googlesource.com/external/repo.git'],
        kwargs={'cwd': cwd})
    command_mock.AddCmdResult(['repo', 'sync', '-j8'],
                              kwargs={'cwd': cwd})
    return command_mock

  def testSetupCrosRepo(self):
    """Tests SetupCrosRepo() by verifying commands it emits."""
    evaluator = self.GetDefaultEvaluator()
    unused_command_mock = self.CreateCommandMockForRepo(evaluator.cros_dir)
    evaluator.SetupCrosRepo()

  def testMaySetupBoardAlreadyDone(self):
    """Tests MaySetupBoard() that board is already set."""
    evaluator = self.GetDefaultEvaluator()

    # mkdir board path inside chroot.
    self.SkipMaySetupBoard(evaluator)
    self.assertTrue(evaluator.MaySetupBoard())

  def testMaySetupBoard(self):
    """Tests MaySetupBoard()."""
    evaluator = self.GetDefaultEvaluator()
    command_mock = self.CreateCommandMockForRepo(evaluator.cros_dir)
    kwargs_run_chroot = {
        'enter_chroot': True,
        'chroot_args': ['--chrome_root', evaluator.chromium_dir, '--no-ns-pid'],
        'cwd': evaluator.cros_dir}
    command_mock.AddCmdResult(
        ['./setup_board', '--board', self.BOARD], kwargs=kwargs_run_chroot)
    command_mock.AddCmdResult(
        ['./build_packages', '--board', self.BOARD], kwargs=kwargs_run_chroot)

    self.assertTrue(evaluator.MaySetupBoard())

  def testMaySetupBoardBuildPackageFailed(self):
    """Tests MaySetupBoard()."""
    evaluator = self.GetDefaultEvaluator()
    command_mock = self.CreateCommandMockForRepo(evaluator.cros_dir)
    kwargs_run_chroot = {
        'enter_chroot': True,
        'chroot_args': ['--chrome_root', evaluator.chromium_dir, '--no-ns-pid'],
        'cwd': evaluator.cros_dir}
    command_mock.AddCmdResult(
        ['./setup_board', '--board', self.BOARD], kwargs=kwargs_run_chroot)

    command_mock.AddCmdResult(
        ['./build_packages', '--board', self.BOARD], kwargs=kwargs_run_chroot,
        returncode=1)

    self.assertFalse(evaluator.MaySetupBoard())