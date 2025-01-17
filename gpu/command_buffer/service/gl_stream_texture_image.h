// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef GPU_COMMAND_BUFFER_SERVICE_GL_STREAM_TEXTURE_IMAGE_H_
#define GPU_COMMAND_BUFFER_SERVICE_GL_STREAM_TEXTURE_IMAGE_H_

#include "gpu/gpu_export.h"
#include "ui/gl/gl_image.h"

namespace gpu {
namespace gles2 {

// Specialization of GLImage that allows us to support (stream) textures
// that supply a texture matrix.
class GPU_EXPORT GLStreamTextureImage : public gl::GLImage {
 public:
  GLStreamTextureImage() {}

  // Get the matrix.
  // Copy the texture matrix for this image into |matrix|.
  // Subclasses must return a matrix appropriate for a coordinate system where
  // UV=(0,0) corresponds to the top left corner of the image.
  virtual void GetTextureMatrix(float matrix[16]) = 0;

  void Flush() override {}

  virtual void NotifyPromotionHint(bool promotion_hint,
                                   int display_x,
                                   int display_y,
                                   int display_width,
                                   int display_height) {}

 protected:
  ~GLStreamTextureImage() override {}

  // Convenience function for subclasses that deal with SurfaceTextures, whose
  // coordinate system has (0,0) at the bottom left of the image.
  // [ a e i m ] [ 1  0 0 0 ]   [ a -e i m+e ]
  // [ b f j n ] [ 0 -1 0 1 ] = [ b -f j n+f ]
  // [ c g k o ] [ 0  0 1 0 ]   [ c -g k o+g ]
  // [ d h l p ] [ 0  0 0 1 ]   [ d -h l p+h ]
  static void YInvertMatrix(float matrix[16]) {
    for (int i = 0; i < 4; ++i) {
      matrix[i + 12] += matrix[i + 4];
      matrix[i + 4] = -matrix[i + 4];
    }
  }

 private:
  DISALLOW_COPY_AND_ASSIGN(GLStreamTextureImage);
};

}  // namespace gles2
}  // namespace gpu

#endif  // GPU_COMMAND_BUFFER_SERVICE_GL_STREAM_TEXTURE_IMAGE_H_
