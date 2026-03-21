import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class AuthService {
  final LocalAuthentication _localAuth = LocalAuthentication();

  /// Sign in with email and password via Supabase.
  /// Returns the user session on success, throws on failure.
  Future<Session> signInWithEmail(String email, String password) async {
    final response = await Supabase.instance.client.auth.signInWithPassword(
      email: email,
      password: password,
    );
    if (response.session == null) {
      throw Exception('Sign in failed');
    }
    return response.session!;
  }

  /// Sign out and clear stored session.
  Future<void> signOut() async {
    await Supabase.instance.client.auth.signOut();
  }

  /// Returns current session JWT token, or null if not signed in.
  String? get currentToken =>
      Supabase.instance.client.auth.currentSession?.accessToken;

  /// Returns current user id, or null.
  String? get currentUserId =>
      Supabase.instance.client.auth.currentUser?.id;

  /// Check if biometrics are available on this device.
  Future<bool> isBiometricAvailable() async {
    try {
      return await _localAuth.canCheckBiometrics &&
          await _localAuth.isDeviceSupported();
    } on PlatformException {
      return false;
    }
  }

  /// Prompt Face ID / fingerprint auth. Returns true if authenticated.
  Future<bool> authenticateWithBiometrics() async {
    try {
      return await _localAuth.authenticate(
        localizedReason: 'Authenticate to access SharpEdge',
        options: const AuthenticationOptions(
          biometricOnly: false, // allow PIN as fallback
          stickyAuth: true,
        ),
      );
    } on PlatformException {
      return false;
    }
  }

  /// Returns true if user has an active Supabase session.
  bool get isSignedIn =>
      Supabase.instance.client.auth.currentSession != null;

  /// Returns the user's subscription tier from JWT app_metadata.
  /// Values: 'free', 'pro', 'sharp'. Defaults to 'free' if not set.
  String get currentTier {
    final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
    return (meta?['tier'] as String?) ?? 'free';
  }

  /// Returns true if the current user is the platform operator.
  /// Operator access is set manually in Supabase — never exposed to subscribers.
  bool get isOperator {
    final meta = Supabase.instance.client.auth.currentUser?.appMetadata;
    return meta?['is_operator'] == true;
  }
}
