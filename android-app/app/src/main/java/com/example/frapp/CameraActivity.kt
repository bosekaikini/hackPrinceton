package com.example.frapp

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.content.ContextWrapper
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.io.IOException
import java.util.UUID
import io.ktor.client.HttpClient
import io.ktor.client.engine.android.Android
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.time.LocalDateTime
import android.location.Location
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices
import io.ktor.client.statement.bodyAsText
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

// Standard Serial Port Profile (SPP) UUID - MUST match the server UUID on the Pi
private val MY_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")

// MAC address of your paired Raspberry Pi (Your value is used here)
// Change this line in your CameraActivity.kt file
private const val RASPBERRY_PI_MAC_ADDRESS = "DC:A6:32:4C:CC:AC" // <-- Changed to UPPECASE
private const val SIGNAL_MESSAGE = "TAKE_PICTURE_SIGNAL\n"

// Replace with the actual URL for your image categorization API
// Change to the IP/Domain of your Python Flask server, NOT the final server
private const val IMAGE_API_ENDPOINT = "http://your-server-ip:8080/api/v1/classify/urban-issue"

// ... rest of your code

// Replace with the IP address and port where you want to send the final JSON
private const val FINAL_SERVER_IP = "http://10.25.11.159:5000"


@Serializable
data class ImageMetaData(
    val categorization: String,
    val latitude: Double,
    val longitude: Double,
    val timestamp: String
)

class CameraActivity : ComponentActivity() {

    private val bluetoothAdapter: BluetoothAdapter? = BluetoothAdapter.getDefaultAdapter()
    private lateinit var fusedLocationClient: FusedLocationProviderClient

    // HTTP Client initialized once
    private val httpClient = HttpClient(Android) {
        install(ContentNegotiation) {
            json(Json { ignoreUnknownKeys = true })
        }
    }

    // ====================================================================
    // 1. PERMISSION HANDLERS
    // ====================================================================

    // Launcher for handling Bluetooth permissions (Android 12+)
    private val bluetoothPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val granted = permissions.entries.all { it.value }
        if (granted) {
            // Bluetooth OK, now check Location
            checkLocationPermissionAndConnect()
        } else {
            Toast.makeText(
                this,
                "Bluetooth permissions denied. Cannot connect to Pi.",
                Toast.LENGTH_SHORT
            ).show()
        }
    }

    // Launcher for handling Location permission
    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            // Location OK, start the full process
            connectAndSendSignal()
        } else {
            Toast.makeText(
                this,
                "Location permission denied. Sending default location.",
                Toast.LENGTH_SHORT
            ).show()
            // Even if denied, we proceed to connect, but will send zeroed location data
            connectAndSendSignal()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        setContent { MaterialTheme { CameraScreen(onBack = { finish() }) } }
    }

    // ====================================================================
    // 2. PERMISSION CHECKING FLOW
    // ====================================================================

    /**
     * Entry point: Checks Bluetooth status and permissions first.
     */
    fun attemptSendSignal() {
        if (bluetoothAdapter == null) {
            Toast.makeText(this, "Bluetooth not supported on this device.", Toast.LENGTH_LONG)
                .show()
            return
        }
        if (!bluetoothAdapter.isEnabled) {
            Toast.makeText(this, "Please enable Bluetooth first.", Toast.LENGTH_LONG).show()
            return
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.BLUETOOTH_CONNECT
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                // Bluetooth permissions granted, proceed to check location
                checkLocationPermissionAndConnect()
            } else {
                // Request both necessary permissions for Android 12+
                bluetoothPermissionLauncher.launch(
                    arrayOf(
                        Manifest.permission.BLUETOOTH_SCAN,
                        Manifest.permission.BLUETOOTH_CONNECT
                    )
                )
            }
        } else {
            // Older Android versions, proceed to check location
            checkLocationPermissionAndConnect()
        }
    }

    /**
     * Checks and requests Location permission (called after Bluetooth is confirmed).
     */
    private fun checkLocationPermissionAndConnect() {
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            // All permissions granted, start the process!
            connectAndSendSignal()
        } else {
            // Request Location permission
            locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    // ====================================================================
    // 3. CORE LOGIC FUNCTIONS
    // ====================================================================

    /**
     * Asynchronously fetches the last known location.
     */
    @SuppressLint("MissingPermission")
    private suspend fun getCurrentLocation(): Location {
        // This is safe because it's only called after permission is granted or explicitly denied
        return suspendCancellableCoroutine { continuation ->
            fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
                if (location != null) {
                    continuation.resume(location)
                } else {
                    // If last location is null, return a zeroed location
                    val defaultLocation =
                        Location("default").apply { latitude = 0.0; longitude = 0.0 }
                    continuation.resume(defaultLocation)
                }
            }.addOnFailureListener { e ->
                // If location fetching fails entirely, resume with an error location
                val errorLocation = Location("error").apply { latitude = -1.0; longitude = -1.0 }
                Log.e("LOCATION", "Failed to fetch location: ${e.message}")
                continuation.resume(errorLocation)
            }
        }
    }

    /**
     * Simulates calling an external API to categorize the image data.
     */
// ... other imports

    @Serializable
    data class CategorizationRequest(val image_base64: String)

    @Serializable
    data class CategorizationResponse(
        val category: String,
        val success: Boolean,
        val error_message: String? = null
    )

    private suspend fun categorizeImage(imageData: ByteArray): String {
        try {
            // Encode the raw image bytes to Base64 for transport in the JSON body
            val base64Image =
                android.util.Base64.encodeToString(imageData, android.util.Base64.NO_WRAP)

            val requestBody = CategorizationRequest(base64Image)
            val jsonBody = Json.encodeToString(requestBody)

            val response = httpClient.post(IMAGE_API_ENDPOINT) {
                contentType(ContentType.Application.Json)
                setBody(jsonBody)
            }

            // Deserialize the response from your custom API
            val apiResponse = Json.decodeFromString<CategorizationResponse>(response.bodyAsText())

            if (apiResponse.success) {
                // Your app receives a clean, categorized string from your "custom ML"
                return apiResponse.category
            } else {
                Log.e("API_CALL", "Custom ML API call failed: ${apiResponse.error_message}")
                return "Uncategorized (ML Failure)"
            }

        } catch (e: Exception) {
            Log.e("API_CALL", "Image categorization failed: ${e.message}")
            return "Uncategorized (Network Error)"
        }
    }

    /**
     * Sends the final packaged JSON metadata to the final server endpoint.
     */
    private suspend fun sendMetaDataToServer(metaData: ImageMetaData) {
        try {
            val jsonBody = Json.encodeToString(metaData)

            val response = httpClient.post(FINAL_SERVER_IP) {
                contentType(ContentType.Application.Json)
                setBody(jsonBody)
            }

            if (response.status.value in 200..299) {
                Log.d("HTTP_POST", "Successfully sent data to server: ${response.status}")
            } else {
                Log.e("HTTP_POST", "Failed to send data. Status: ${response.status}")
            }
        } catch (e: Exception) {
            Log.e("HTTP_POST", "Failed to connect/send data to final server: ${e.message}")
        }
    }


    // ====================================================================
    // 4. ORCHESTRATOR FUNCTION
    // ====================================================================

    /**
     * Establishes connection, sends signal, receives image, processes, and sends JSON.
     */
    // In CameraActivity.kt, replace the entire `connectAndSendSignal()` function with this:

    /**
     * Establishes connection, sends signal, receives image, processes, and sends JSON.
     */
    @SuppressLint("MissingPermission")
    private fun connectAndSendSignal() {
        CoroutineScope(Dispatchers.IO).launch {
            var socket: BluetoothSocket? = null
            var receivedImageData: ByteArray? = null // Change to nullable ByteArray
            try {
                // 1. Bluetooth Connection and Signal Send
                val device: BluetoothDevice =
                    bluetoothAdapter!!.getRemoteDevice(RASPBERRY_PI_MAC_ADDRESS.uppercase()) // Force uppercase for safety
                socket = device.createRfcommSocketToServiceRecord(MY_UUID)
                bluetoothAdapter.cancelDiscovery()
                socket.connect()
                socket.outputStream.write(SIGNAL_MESSAGE.toByteArray())
                Log.d("BT_COMM", "Signal sent: $SIGNAL_MESSAGE")

                // 2. RECEIVE IMAGE DATA (Protocol: 4-byte size header + Body)
                val inputStream = socket.inputStream

                // Read 4-byte header
                val sizeHeader = ByteArray(4)
                var bytesRead = inputStream.read(sizeHeader)
                if (bytesRead != 4) {
                    throw IOException("Failed to read image size header.")
                }

                // Convert 4 bytes to an integer (Big-Endian/Network Byte Order)
                val imageSize =
                    java.nio.ByteBuffer.wrap(sizeHeader).order(java.nio.ByteOrder.BIG_ENDIAN)
                        .getInt()

                if (imageSize <= 0) {
                    // This signals an error/failure from the Pi
                    val errorBuffer = ByteArray(100)
                    val errorBytes = inputStream.read(errorBuffer)
                    val errorMessage = if (errorBytes > 0) String(
                        errorBuffer,
                        0,
                        errorBytes
                    ) else "Unknown Pi Error"
                    throw IOException("Pi failed to capture image. Error: $errorMessage")
                }

                // Read the image body
                receivedImageData = ByteArray(imageSize)
                var totalBytesRead = 0
                while (totalBytesRead < imageSize) {
                    bytesRead = inputStream.read(
                        receivedImageData,
                        totalBytesRead,
                        imageSize - totalBytesRead
                    )
                    if (bytesRead == -1) {
                        throw IOException("Connection closed prematurely while reading image body.")
                    }
                    totalBytesRead += bytesRead
                }
                Log.d("BT_COMM", "Successfully received image body: $totalBytesRead bytes.")


                // 3. PROCESS DATA (Only if image was received)
                if (receivedImageData.isNotEmpty()) {
                    val categorization = categorizeImage(receivedImageData)
                    val location = getCurrentLocation()
                    val timestamp = LocalDateTime.now()
                        .format(java.time.format.DateTimeFormatter.ISO_LOCAL_DATE_TIME)

                    // 4. PACKAGE AND SEND JSON
                    val metaData = ImageMetaData(
                        categorization = categorization,
                        latitude = location.latitude,
                        longitude = location.longitude,
                        timestamp = timestamp
                    )
                    sendMetaDataToServer(metaData)

                    // 5. NAVIGATION (Pass the image data and metadata to ProfileActivity)
                    val intent =
                        android.content.Intent(this@CameraActivity, ProfileActivity::class.java)
                            .apply {
                                putExtra("IMAGE_DATA", receivedImageData) // Pass the image bytes
                                putExtra("CATEGORIZATION", categorization)  // Pass metadata
                                // Add other metadata if needed
                            }
                    startActivity(intent)

                    runOnUiThread {
                        Toast.makeText(
                            this@CameraActivity,
                            "Data processed, sent to server, and navigated!",
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
                // 6. Close the socket
                try {
                    socket?.close()
                } catch (closeException: IOException) {
                    Log.e("BT_COMM", "Could not close the client socket", closeException)
                }
            }
        }
    }

    fun findActivity(context: Context): Activity? {
        if (context is Activity) return context
        if (context is ContextWrapper) return findActivity(context.baseContext)
        return null
    }

    @Composable
    fun CameraScreen(onBack: () -> Unit) {
        // Safely cast the LocalContext to the CameraActivity instance (Fixes previous error)
        val context = LocalContext.current
        val activity = findActivity(context) as? CameraActivity ?: return

        Scaffold { padding ->
            Box(
                Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center
            ) {
                Button(
                    // Calls the permission/connect flow on button click
                    onClick = { activity.attemptSendSignal() },
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text("Take Picture (Send Bluetooth Signal)")
                }
            }
        }
    }
}