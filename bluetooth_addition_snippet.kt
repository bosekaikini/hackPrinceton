@SuppressLint("MissingPermission")
private fun connectAndSendSignal() {
    CoroutineScope(Dispatchers.IO).launch {
        var socket: BluetoothSocket? = null
        var receivedImageData: ByteArray? = null
        try {
            // 1) Connect & send trigger
            val device: BluetoothDevice =
                bluetoothAdapter!!.getRemoteDevice(RASPBERRY_PI_MAC_ADDRESS.uppercase())
            socket = device.createRfcommSocketToServiceRecord(MY_UUID)
            bluetoothAdapter?.cancelDiscovery()
            socket.connect()
            socket.outputStream.write(SIGNAL_MESSAGE.toByteArray())
            Log.d("BT_COMM", "Signal sent: $SIGNAL_MESSAGE")

            // 2) Receive image (protocol: 4-byte big-endian size + body)
            val inputStream = socket.inputStream

            val sizeHeader = ByteArray(4)
            var bytesRead = inputStream.read(sizeHeader)
            if (bytesRead != 4) throw IOException("Failed to read image size header.")

            val imageSize = java.nio.ByteBuffer.wrap(sizeHeader)
                .order(java.nio.ByteOrder.BIG_ENDIAN).getInt()

            if (imageSize <= 0) {
                // read optional error text
                val buf = ByteArray(256)
                val n = inputStream.read(buf)
                val msg = if (n > 0) String(buf, 0, n) else "Unknown Pi Error"
                throw IOException("Pi failed to capture image. Error: $msg")
            }

            receivedImageData = ByteArray(imageSize)
            var total = 0
            while (total < imageSize) {
                bytesRead = inputStream.read(receivedImageData!!, total, imageSize - total)
                if (bytesRead == -1) throw IOException("Socket closed while reading image body.")
                total += bytesRead
            }
            Log.d("BT_COMM", "Received image: $total bytes")

            // 3) If we have image bytes: SAVE to Photos, then continue pipeline
            if (receivedImageData != null && receivedImageData!!.isNotEmpty()) {

                // --- Save to Photos (Pictures/UrbanSight) ---
                val resolver = applicationContext.contentResolver
                val fileName = "urbansight_${System.currentTimeMillis()}.png"
                val values = android.content.ContentValues().apply {
                    put(android.provider.MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                    put(android.provider.MediaStore.MediaColumns.MIME_TYPE, "image/png")
                    put(android.provider.MediaStore.MediaColumns.RELATIVE_PATH, "Pictures/UrbanSight")
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                        put(android.provider.MediaStore.MediaColumns.IS_PENDING, 1)
                    }
                }

                val uri = resolver.insert(
                    android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
                )
                if (uri != null) {
                    resolver.openOutputStream(uri)?.use { out ->
                        out.write(receivedImageData)
                    }
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                        values.clear()
                        values.put(android.provider.MediaStore.MediaColumns.IS_PENDING, 0)
                        resolver.update(uri, values, null, null)
                    }
                    Log.d("BT_COMM", "Saved image to $uri")
                } else {
                    Log.e("BT_COMM", "Failed to create MediaStore entry for image")
                }

                // --- Continue with your pipeline ---
                val categorization = categorizeImage(receivedImageData!!)
                val location = getCurrentLocation()
                val timestamp = LocalDateTime.now()
                    .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME)

                val metaData = ImageMetaData(
                    categorization = categorization,
                    latitude = location.latitude,
                    longitude = location.longitude,
                    timestamp = timestamp
                )
                sendMetaDataToServer(metaData)

                val intent = android.content.Intent(this@CameraActivity, ProfileActivity::class.java)
                    .apply {
                        putExtra("IMAGE_DATA", receivedImageData) // pass image bytes
                        putExtra("CATEGORIZATION", categorization)
                    }
                startActivity(intent)

                runOnUiThread {
                    Toast.makeText(
                        this@CameraActivity,
                        "Saved to Photos (Pictures/UrbanSight) and processed.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            } else {
                runOnUiThread {
                    Toast.makeText(
                        this@CameraActivity,
                        "No image data received from Pi.",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }

        } catch (e: Exception) {
            Log.e("BT_COMM", "Full process failed: ${e.message}")
            runOnUiThread {
                Toast.makeText(
                    this@CameraActivity,
                    "Process Failed: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
        } finally {
            try { socket?.close() } catch (_: IOException) {}
        }
    }
}
