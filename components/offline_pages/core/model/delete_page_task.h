// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef COMPONENTS_OFFLINE_PAGES_CORE_MODEL_DELETE_PAGE_TASK_H_
#define COMPONENTS_OFFLINE_PAGES_CORE_MODEL_DELETE_PAGE_TASK_H_

#include <memory>
#include <vector>

#include "base/macros.h"
#include "base/memory/weak_ptr.h"
#include "components/offline_pages/core/offline_page_metadata_store.h"
#include "components/offline_pages/core/offline_page_model.h"
#include "components/offline_pages/core/offline_page_types.h"
#include "components/offline_pages/core/task.h"

namespace sql {
class Connection;
}  // namespace sql

namespace offline_pages {

struct ClientId;
class OfflinePageMetadataStoreSQL;

// Task that deletes pages from the metadata store. It takes the store and
// archive manager for deleting entries from database and file system. Also the
// task needs to be constructed with a DeleteFunction, which defines which pages
// are going to be deleted.
// The caller needs to provide a callback which takes a vector of pages that are
// deleted, along with a DeletePageResult.
// The tasks have to be created by using the static CreateTask* methods.
class DeletePageTask : public Task {
 public:
  struct DeletePageTaskResult {
    DeletePageTaskResult();
    DeletePageTaskResult(
        DeletePageResult result,
        const std::vector<OfflinePageModel::DeletedPageInfo>& infos);
    DeletePageTaskResult(const DeletePageTaskResult& other);
    ~DeletePageTaskResult();

    DeletePageResult result;
    std::vector<OfflinePageModel::DeletedPageInfo> infos;
  };
  typedef base::OnceCallback<void(
      DeletePageResult,
      const std::vector<OfflinePageModel::DeletedPageInfo>&)>
      DeletePageTaskCallback;

  // Create a task to delete pages with offline ids in |offline_ids|.
  static std::unique_ptr<DeletePageTask> CreateTaskMatchingOfflineIds(
      OfflinePageMetadataStoreSQL* store,
      const std::vector<int64_t>& offline_ids,
      DeletePageTask::DeletePageTaskCallback callback);

  // Create a task to delete pages with client ids in |client_ids|.
  static std::unique_ptr<DeletePageTask> CreateTaskMatchingClientIds(
      OfflinePageMetadataStoreSQL* store,
      const std::vector<ClientId>& client_ids,
      DeletePageTask::DeletePageTaskCallback callback);

  // Create a task to delete pages which satisfy |predicate|.
  static std::unique_ptr<DeletePageTask>
  CreateTaskMatchingUrlPredicateForCachedPages(
      OfflinePageMetadataStoreSQL* store,
      const UrlPredicate& predicate,
      DeletePageTask::DeletePageTaskCallback callback);

  ~DeletePageTask() override;

  // Task implementation.
  void Run() override;

 private:
  typedef base::OnceCallback<DeletePageTaskResult(sql::Connection*)>
      DeleteFunction;

  // Making the constructor private, in order to use static methods to create
  // tasks.
  DeletePageTask(OfflinePageMetadataStoreSQL* store,
                 DeleteFunction func,
                 DeletePageTaskCallback callback);

  void DeletePages();
  void OnDeletePageDone(DeletePageTaskResult result);
  void OnDeleteArchiveFilesDone(
      std::unique_ptr<OfflinePagesUpdateResult> result,
      bool delete_files_result);
  void InformDeletePageDone(DeletePageResult result);

  // The store to delete pages from. Not owned.
  OfflinePageMetadataStoreSQL* store_;
  // The function which will delete pages.
  DeleteFunction func_;
  DeletePageTaskCallback callback_;

  base::WeakPtrFactory<DeletePageTask> weak_ptr_factory_;
  DISALLOW_COPY_AND_ASSIGN(DeletePageTask);
};

}  // namespace offline_pages

#endif  // COMPONENTS_OFFLINE_PAGES_CORE_MODEL_DELETE_PAGE_TASK_H_
