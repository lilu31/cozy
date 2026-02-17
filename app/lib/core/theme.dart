import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // New Palette: Ultramodern Terracotta
  static const Color cream = Color(0xFFFFF3E4); // Warm Sand (Reference Match)
  static const Color terracotta = Color(0xFFE76F51); // Balanced Burnt Sienna
  static const Color mildTerracotta = Color(0xFFF4A261); // Sandy Orange
  static const Color warmYellow = Color(0xFFF2CC8F); // Solar/Highlight
  static const Color richGold = Color(0xFFE09F3E); // Deep Gold
  static const Color dullRed = Color(0xFFD64045); // Accent/Alert
  static const Color charcoal = Color(0xFF3D405B); // Text/Dark
  static const Color softGrey = Color(0xFFE0E0E0);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: cream,
      colorScheme: ColorScheme.fromSeed(
        seedColor: terracotta,
        background: cream,
        surface: cream,
        primary: terracotta,
        secondary: warmYellow,
        tertiary: dullRed,
      ),
      textTheme: GoogleFonts.outfitTextTheme().apply(
        bodyColor: charcoal,
        displayColor: terracotta,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: cream,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: charcoal),
        titleTextStyle: GoogleFonts.plusJakartaSans(
          color: terracotta,
          fontSize: 32,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.5, 
        ),
      ),
      cardTheme: CardTheme(
        color: Colors.white.withOpacity(0.9), // Slight transparency for glass feel
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(32), // More rounded
          side: const BorderSide(color: Color(0xFFF0F0F0), width: 1),
        ),
      ),
    );
  }
}
