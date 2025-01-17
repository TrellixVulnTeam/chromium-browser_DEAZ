// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "device/hid/hid_connection_impl.h"

#include "base/bind.h"
#include "base/memory/ptr_util.h"

namespace device {

HidConnectionImpl::HidConnectionImpl(
    scoped_refptr<device::HidConnection> connection)
    : hid_connection_(std::move(connection)), weak_factory_(this) {}

HidConnectionImpl::~HidConnectionImpl() {
  DCHECK(hid_connection_);

  // Close |hid_connection_| on destruction because this class is owned by a
  // mojo::StrongBinding and will be destroyed when the pipe is closed.
  hid_connection_->Close();
}

void HidConnectionImpl::Read(ReadCallback callback) {
  DCHECK(hid_connection_);
  hid_connection_->Read(base::BindOnce(&HidConnectionImpl::OnRead,
                                       weak_factory_.GetWeakPtr(),
                                       std::move(callback)));
}

void HidConnectionImpl::OnRead(ReadCallback callback,
                               bool success,
                               scoped_refptr<net::IOBuffer> buffer,
                               size_t size) {
  if (!success) {
    std::move(callback).Run(false, 0, base::nullopt);
    return;
  }
  DCHECK(buffer);

  std::vector<uint8_t> data(buffer->data() + 1, buffer->data() + size);
  std::move(callback).Run(true, buffer->data()[0], data);
}

void HidConnectionImpl::Write(uint8_t report_id,
                              const std::vector<uint8_t>& buffer,
                              WriteCallback callback) {
  DCHECK(hid_connection_);

  auto io_buffer =
      base::MakeRefCounted<net::IOBufferWithSize>(buffer.size() + 1);
  io_buffer->data()[0] = report_id;

  const char* data = reinterpret_cast<const char*>(buffer.data());
  memcpy(io_buffer->data() + 1, data, buffer.size());

  hid_connection_->Write(
      io_buffer, io_buffer->size(),
      base::BindOnce(&HidConnectionImpl::OnWrite, weak_factory_.GetWeakPtr(),
                     std::move(callback)));
}

void HidConnectionImpl::OnWrite(WriteCallback callback, bool success) {
  std::move(callback).Run(success);
}

void HidConnectionImpl::GetFeatureReport(uint8_t report_id,
                                         GetFeatureReportCallback callback) {
  DCHECK(hid_connection_);
  hid_connection_->GetFeatureReport(
      report_id,
      base::BindOnce(&HidConnectionImpl::OnGetFeatureReport,
                     weak_factory_.GetWeakPtr(), std::move(callback)));
}

void HidConnectionImpl::OnGetFeatureReport(GetFeatureReportCallback callback,
                                           bool success,
                                           scoped_refptr<net::IOBuffer> buffer,
                                           size_t size) {
  if (!success) {
    std::move(callback).Run(false, base::nullopt);
    return;
  }
  DCHECK(buffer);

  std::vector<uint8_t> data(buffer->data(), buffer->data() + size);
  std::move(callback).Run(true, data);
}

void HidConnectionImpl::SendFeatureReport(uint8_t report_id,
                                          const std::vector<uint8_t>& buffer,
                                          SendFeatureReportCallback callback) {
  DCHECK(hid_connection_);

  auto io_buffer =
      base::MakeRefCounted<net::IOBufferWithSize>(buffer.size() + 1);
  io_buffer->data()[0] = report_id;

  const char* data = reinterpret_cast<const char*>(buffer.data());
  memcpy(io_buffer->data() + 1, data, buffer.size());

  hid_connection_->SendFeatureReport(
      io_buffer, io_buffer->size(),
      base::BindOnce(&HidConnectionImpl::OnSendFeatureReport,
                     weak_factory_.GetWeakPtr(), std::move(callback)));
}

void HidConnectionImpl::OnSendFeatureReport(SendFeatureReportCallback callback,
                                            bool success) {
  std::move(callback).Run(success);
}

}  // namespace device
