package com.example.frapp

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationServices

class MainActivity : ComponentActivity() {

    // Fused Location Provider Client instance
    private lateinit var fusedLocationClient: FusedLocationProviderClient

    // State to hold the collected location data
    private var currentLocation by mutableStateOf("Location: Unknown")

    // Launcher for handling the runtime permission request
    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            // Permission granted, attempt to get location
            getLocation()
        } else {
            // Permission denied, update state and show a message
            currentLocation = "Location: Permission Denied"
            Toast.makeText(this, "Location access denied.", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize the Fused Location Provider
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)

        // Request location upon startup
        requestLocation()

        setContent {
            MaterialTheme {
                PrivacyScreen(
                    onOpenProfile = { startActivity(Intent(this, ProfileActivity::class.java)) },
                    onOpenCamera = { startActivity(Intent(this, CameraActivity::class.java)) },
                    locationStatus = currentLocation
                )
            }
        }
    }

    private fun requestLocation() {
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            // Permission already granted, get location
            getLocation()
        } else {
            // Request permission
            locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    // Annotation needed because we are checking permission just above this call
    @SuppressLint("MissingPermission")
    private fun getLocation() {
        fusedLocationClient.lastLocation.addOnSuccessListener { location: Location? ->
            if (location != null) {
                currentLocation = "Lat: ${location.latitude}, Lon: ${location.longitude}"
            } else {
                currentLocation = "Location: Not Available (Try again)"
            }
        }.addOnFailureListener {
            currentLocation = "Location: Failed to fetch"
        }
    }
}


@Composable
fun PrivacyScreen(
    onOpenProfile: () -> Unit,
    onOpenCamera: () -> Unit,
    locationStatus: String // <-- NEW PARAMETER TO DISPLAY LOCATION
) {
    // NOTE: locationAllowed is now only a VISUAL toggle, not the real permission flag
    var locationAllowed by remember { mutableStateOf(false) }
    var cameraAllowed by remember { mutableStateOf(false) }
    var timeRange by remember { mutableStateOf(6f..22f) }

    Scaffold { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {

            // Display the REAL collected location status
            Text(
                text = "Last Location Data:",
                style = MaterialTheme.typography.titleMedium
            )
            Text(text = locationStatus)

            Divider(Modifier.padding(vertical = 10.dp))

            // Location Allowed? (The user-facing toggle)
            Button(
                onClick = { locationAllowed = !locationAllowed },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (locationAllowed) "Location Permission Toggle: ON" else "Location Permission Toggle: OFF")
            }

            // ... (Rest of your UI code remains here) ...

            // Camera Allowed? (toggle)
            Button(
                onClick = { cameraAllowed = !cameraAllowed },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (cameraAllowed) "Camera Allowed (ON)" else "Camera Allowed (OFF)")
            }

            // Camera time of day slider (start–end)
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Camera time of day")
                RangeSlider(
                    value = timeRange,
                    onValueChange = { timeRange = it },
                    valueRange = 0f..24f,
                    steps = 23
                )
                Text("Active: ${hourStr(timeRange.start)} — ${hourStr(timeRange.endInclusive)}")
            }

            Spacer(Modifier.height(8.dp))

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(onClick = onOpenProfile, modifier = Modifier.weight(1f)) {
                    Text("Open Profile")
                }

                // Camera button logic remains independent of the location toggle
                Button(
                    onClick = onOpenCamera,
                    enabled = cameraAllowed,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Open Camera")
                }
            }
        }
    }
}

private fun hourStr(h: Float): String {
    val hour = h.toInt()
    val minutes = ((h - hour) * 60f).toInt()
    return "%02d:%02d".format(hour, minutes)
}