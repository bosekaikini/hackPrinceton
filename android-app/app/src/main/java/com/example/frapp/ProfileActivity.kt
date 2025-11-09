package com.example.frapp

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text

class ProfileActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { ProfileScreen(onBack = { finish() }) } }
    }
}

@Composable
fun ProfileScreen(onBack: () -> Unit) {
    var name by remember { mutableStateOf("") }
    var bio by remember { mutableStateOf("") }

    // Removed the 'topBar' parameter entirely
    Scaffold { padding ->
        Column(
            Modifier
                .fillMaxSize()
                // Apply the Scaffold padding, and your custom padding
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Since the TopAppBar and its back button are gone,
            // you might want a button here to navigate back if needed,
            // but for now, we'll keep the onBack functionality available
            // for a custom element if you add one.

            Button(onClick = onBack) {
                Text("Go Back")
            }

            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("User name") },
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = bio,
                onValueChange = { bio = it },
                label = { Text("User bio") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 3
            )

            Text("Pictures")

            // Placeholder area for pictures
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(220.dp)
                    .border(1.dp, Color.Gray, RoundedCornerShape(12.dp))
                    .background(Color(0xFFF6F6F6), RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text("Picture area (placeholder)")
            }
        }
    }
}