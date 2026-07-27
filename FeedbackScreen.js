import React, { useState } from "react";
import {
  View, Text, ScrollView, TextInput, TouchableOpacity, StyleSheet, Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { api, errText } from "../api";
import { theme } from "../theme";

const EXP = [
  ["Excellent", "happy-outline"], ["Good", "happy-outline"],
  ["Average", "remove-circle-outline"], ["Poor", "sad-outline"],
];

export default function FeedbackScreen({ route, navigation }) {
  const p = route.params?.product || {};
  const [rating, setRating] = useState(0);
  const [experience, setExperience] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!rating) { Alert.alert("Feedback", "Please rate your experience."); return; }
    if (!message.trim()) { Alert.alert("Feedback", "Please write your feedback."); return; }
    setBusy(true);
    try {
      await api.feedback(p.product_id, rating, experience, message.trim(), "");
      Alert.alert("💬 Thank You!", "Your feedback has been submitted.",
        [{ text: "OK", onPress: () => navigation.goBack() }]);
    } catch (e) { Alert.alert("Error", errText(e)); } finally { setBusy(false); }
  }

  return (
    <ScrollView style={{ backgroundColor: theme.bg }} contentContainerStyle={{ padding: 16, paddingBottom: 30 }}>
      <View style={s.topIcon}><Ionicons name="chatbox-ellipses" size={28} color={theme.pink} /></View>
      <Text style={s.lead}>We'd love to hear your thoughts and suggestions.</Text>
      <Text style={s.leadSub}>Your feedback helps us improve Smart Style Finder.</Text>

      <View style={s.card}>
        <Text style={s.qLabel}>1. Rate your experience</Text>
        <View style={s.stars}>
          {[1, 2, 3, 4, 5].map((v) => (
            <TouchableOpacity key={v} onPress={() => setRating(v)}>
              <Ionicons name={v <= rating ? "star" : "star-outline"} size={36}
                color={v <= rating ? theme.star : theme.pink} style={{ marginHorizontal: 4 }} />
            </TouchableOpacity>
          ))}
        </View>
        <Text style={s.tapRate}>{rating ? `${rating} / 5` : "Tap to rate"}</Text>

        <Text style={s.qLabel}>2. How was your experience?</Text>
        <View style={s.expRow}>
          {EXP.map(([label, icon]) => {
            const on = experience === label;
            return (
              <TouchableOpacity key={label} style={[s.exp, on && s.expOn]} onPress={() => setExperience(label)}>
                <Ionicons name={icon} size={16} color={on ? "#fff" : theme.pink} />
                <Text style={[s.expText, on && { color: "#fff" }]}> {label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={s.qLabel}>3. Your Feedback</Text>
        <TextInput style={s.textarea} multiline maxLength={500}
          placeholder="Share your thoughts, suggestions or any issues…" value={message} onChangeText={setMessage} />
        <Text style={s.counter}>{message.length}/500</Text>
      </View>

      <View style={s.infoRow}>
        <View style={s.info}><Ionicons name="shield-checkmark-outline" size={20} color={theme.pink} />
          <Text style={s.infoTitle}>Secure & Reliable</Text><Text style={s.infoSub}>Your booking is safe with us</Text></View>
        <View style={s.info}><Ionicons name="flash-outline" size={20} color={theme.pink} />
          <Text style={s.infoTitle}>Quick Confirmation</Text><Text style={s.infoSub}>Get confirmation instantly</Text></View>
      </View>

      <TouchableOpacity style={s.submit} onPress={submit} disabled={busy}>
        <Ionicons name="send" size={18} color="#fff" />
        <Text style={s.submitText}>  {busy ? "Submitting…" : "Submit Feedback"}</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  topIcon: { alignSelf: "center", width: 56, height: 56, borderRadius: 16, backgroundColor: theme.pinkSoft, alignItems: "center", justifyContent: "center", marginTop: 6 },
  lead: { textAlign: "center", fontWeight: "700", color: theme.ink, marginTop: 12, fontSize: 15 },
  leadSub: { textAlign: "center", color: theme.muted, marginTop: 4 },
  card: { backgroundColor: "#fff", borderWidth: 1, borderColor: theme.line, borderRadius: 16, padding: 16, marginTop: 16 },
  qLabel: { fontWeight: "700", color: theme.ink, marginTop: 14, marginBottom: 8 },
  stars: { flexDirection: "row", justifyContent: "center" },
  tapRate: { textAlign: "center", color: theme.muted, marginTop: 6 },
  expRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  exp: { flexDirection: "row", alignItems: "center", borderWidth: 1, borderColor: theme.pinkSoft, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9 },
  expOn: { backgroundColor: theme.pink, borderColor: theme.pink },
  expText: { color: theme.pinkDark, fontSize: 13, fontWeight: "600" },
  textarea: { borderWidth: 1, borderColor: theme.line, borderRadius: 12, padding: 12, minHeight: 90, textAlignVertical: "top" },
  counter: { textAlign: "right", color: theme.muted, fontSize: 12, marginTop: 4 },
  infoRow: { flexDirection: "row", gap: 10, marginTop: 14 },
  info: { flex: 1, backgroundColor: theme.pinkTint, borderRadius: 12, padding: 14 },
  infoTitle: { fontWeight: "700", color: theme.ink, fontSize: 13, marginTop: 6 },
  infoSub: { color: theme.muted, fontSize: 11, marginTop: 2 },
  submit: { flexDirection: "row", justifyContent: "center", alignItems: "center", backgroundColor: theme.pink, borderRadius: 12, padding: 16, marginTop: 18 },
  submitText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
