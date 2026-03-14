import 'dart:convert';
import 'dart:io';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;

/// Background message handler — must be top-level function.
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Background messages are shown automatically by FCM on Android.
  // On iOS, content-available:1 wakes the app silently.
}

class NotificationService {
  static final _flutterLocalNotifications = FlutterLocalNotificationsPlugin();
  static const _androidChannel = AndroidNotificationChannel(
    'sharp_alerts',
    'Sharp Alerts',
    description: 'High-alpha betting opportunity alerts',
    importance: Importance.max,
  );

  /// Initialize FCM: background handler, Android channel, iOS permissions,
  /// and foreground message display.
  static Future<void> initialize() async {
    // Register background handler
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    // Android notification channel
    await _flutterLocalNotifications
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_androidChannel);

    // iOS permissions
    await FirebaseMessaging.instance.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    // Foreground notification display (Android requires manual show)
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      final notification = message.notification;
      final android = message.notification?.android;
      if (notification != null && android != null) {
        _flutterLocalNotifications.show(
          notification.hashCode,
          notification.title,
          notification.body,
          NotificationDetails(
            android: AndroidNotificationDetails(
              _androidChannel.id,
              _androidChannel.name,
              channelDescription: _androidChannel.description,
              importance: Importance.max,
              priority: Priority.high,
            ),
          ),
        );
      }
    });
  }

  /// Get FCM token and register it with the API.
  /// Fails silently — token registration is best-effort.
  static Future<void> registerToken({
    required String userId,
    required String authToken,
    required String baseUrl,
  }) async {
    try {
      final fcmToken = await FirebaseMessaging.instance.getToken();
      if (fcmToken == null) return;

      final platform = Platform.isIOS ? 'ios' : 'android';

      await http.post(
        Uri.parse('$baseUrl/api/v1/users/$userId/device-token'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $authToken',
        },
        body: jsonEncode({'fcm_token': fcmToken, 'platform': platform}),
      );
    } catch (_) {
      // Fail silently — token registration is best-effort
    }
  }
}
