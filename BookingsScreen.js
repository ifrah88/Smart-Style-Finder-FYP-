import React, { useCallback, useState } from "react";
import {
  View, Text, Image, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { Ionicons } from "@expo/vector-icons";
import { api, errText } from "../api";
import { theme } from "../theme";

const TABS = ["All", "Pending", "Confirmed", "Completed"];
const STATUS_COLORS = {
  Pending: { bg: "#fdf0d8", fg: "#b8860b" },
  Confirmed: { bg: "#dcf3e3", fg: "#1f8a4c" },
  Completed: { bg: "#dde9fb", fg: "#2b6cb0" },
};
const SORTS = [
  { key: "default", label: "Default" },
  { key: "asc", label: "↑ Low–High" },
  { key: "desc", label: "↓ High–Low" },
];

function parsePrice(p) {
  return parseInt(String(p || "0").replace(/[^0-9]/g, ""), 10) || 0;
}

export default function BookingsScreen({ navigation }) {
  const [items, setItems] = useState(null);
  const [tab, setTab] = useState("All");
  const [sort, setSort] = useState("default");

  const load = useCallback(() => {
    api.bookings().then((d) => setItems(d.bookings)).catch((e) => { Alert.alert("Error", errText(e)); setItems([]); });
  }, []);
  useFocusEffect(useCallback(() => { load(); }, [load]));

  function cancel(b) {
    Alert.alert("Cancel Booking", `Cancel booking ${b.booking_id}?`, [
      { text: "No" },
      { text: "Yes, cancel", style: "destructive", onPress: async () => {
        try { await api.cancelBooking(b.id); load(); } catch (e) { Alert.alert("Error", errText(e)); }
      } },
    ]);
  }

  function confirm(b) {
    Alert.alert("Confirm Booking", `Confirm booking ${b.booking_id}?`, [
      { text: "No" },
      { text: "Yes, confirm", onPress: async () => {
        try {
          await api.confirmBooking(b.id);
          setItems((prev) => prev.map((x) => x.id === b.id ? { ...x, status: "Confirmed" } : x));
        } catch (e) { Alert.alert("Error", errText(e)); }
      } },
    ]);
  }

  const header = (
    <View>
      <Text style={s.title}>My Bookings</Text>
      <View style={s.tabs}>
        {TABS.map((t) => (
          <TouchableOpacity key={t} style={[s.tab, tab === t && s.tabOn]} onPress={() => setTab(t)}>
            <Text style={[s.tabText, tab === t && { color: "#fff" }]}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>
      <View style={s.sortRow}>
        <Text style={s.sortLabel}>Sort by price:</Text>
        {SORTS.map((so) => (
          <TouchableOpacity key={so.key} style={[s.sortBtn, sort === so.key && s.sortBtnOn]}
            onPress={() => setSort(so.key)}>
            <Text style={[s.sortBtnText, sort === so.key && { color: "#fff" }]}>{so.label}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  if (items === null) return <View style={s.center}><ActivityIndicator size="large" color={theme.pink} /></View>;

  let filtered = tab === "All" ? items : items.filter((b) => b.status === tab);
  if (sort === "asc") filtered = [...filtered].sort((a, b) => parsePrice(a.price) - parsePrice(b.price));
  else if (sort === "desc") filtered = [...filtered].sort((a, b) => parsePrice(b.price) - parsePrice(a.price));

  return (
    <View style={{ flex: 1, backgroundColor: theme.bg, paddingTop: 50 }}>
      <FlatList
        data={filtered}
        keyExtractor={(b) => String(b.id)}
        ListHeaderComponent={header}
        contentContainerStyle={{ padding: 16, paddingBottom: 30 }}
        ListEmptyComponent={<View style={s.empty}>
          <Ionicons name="calendar-outline" size={40} color={theme.line} />
          <Text style={s.emptyText}>No {tab !== "All" ? tab.toLowerCase() + " " : ""}bookings yet.</Text>
        </View>}
        ListFooterComponent={filtered.length > 0 ? (
          <View style={s.secure}><Ionicons name="shield-checkmark" size={18} color={theme.pink} />
            <Text style={s.secureText}>  Secure & Reliable — your bookings are safe with us.</Text></View>
        ) : null}
        renderItem={({ item: b }) => {
          const sc = STATUS_COLORS[b.status] || STATUS_COLORS.Pending;
          return (
            <View style={s.card}>
              <View style={{ flexDirection: "row" }}>
                <Image source={{ uri: api.imgUrl(b.img_url) }} style={s.thumb} />
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={s.cTitle} numberOfLines={2}>{b.title}</Text>
                  <Text style={s.cBrand}>by {(b.brand || "").replace(/\b\w/g, (c) => c.toUpperCase())}</Text>
                  <Text style={s.cPrice}>{b.price}</Text>
                  <Row label="Booking Date" value={b.booking_date || "—"} />
                  <Row label="Booking ID" value={b.booking_id} />
                  <Row label="Size" value={b.size} />
                  <View style={s.metaRow}>
                    <Text style={s.metaLabel}>Status</Text>
                    <View style={[s.statusBadge, { backgroundColor: sc.bg }]}>
                      <Text style={[s.statusText, { color: sc.fg }]}>{b.status}</Text>
                    </View>
                  </View>
                </View>
              </View>
              <View style={s.actions}>
                <TouchableOpacity style={s.viewBtn} onPress={() => navigation.navigate("Product", { pid: b.product_id })}>
                  <Ionicons name="eye-outline" size={15} color={theme.pink} /><Text style={s.viewText}> View Details</Text>
                </TouchableOpacity>
                {b.status === "Completed" ? null : b.status === "Confirmed" ? (
                  <TouchableOpacity style={s.trackBtn} onPress={() => Alert.alert("Track Booking", "Your booking is being prepared. 🚚")}>
                    <Ionicons name="navigate-outline" size={15} color="#fff" /><Text style={s.trackText}> Track Booking</Text>
                  </TouchableOpacity>
                ) : (
                  <View style={{ flexDirection: "row", flex: 1, gap: 8 }}>
                    <TouchableOpacity style={[s.confirmBtn, { flex: 1 }]} onPress={() => confirm(b)}>
                      <Ionicons name="checkmark-circle-outline" size={15} color="#fff" /><Text style={s.trackText}> Confirm</Text>
                    </TouchableOpacity>
                    <TouchableOpacity style={[s.cancelBtn, { flex: 1 }]} onPress={() => cancel(b)}>
                      <Ionicons name="close-circle-outline" size={15} color="#fff" /><Text style={s.trackText}> Cancel</Text>
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            </View>
          );
        }}
      />
    </View>
  );
}

function Row({ label, value }) {
  return (
    <View style={s.metaRow}>
      <Text style={s.metaLabel}>{label}</Text>
      <Text style={s.metaValue}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  title: { fontSize: 24, fontWeight: "800", color: theme.ink, textAlign: "center", marginBottom: 14 },
  tabs: { flexDirection: "row", gap: 8, marginBottom: 10 },
  tab: { flex: 1, paddingVertical: 9, borderRadius: 20, alignItems: "center", backgroundColor: theme.pinkTint },
  tabOn: { backgroundColor: theme.pink },
  tabText: { fontSize: 12.5, fontWeight: "600", color: theme.pinkDark },
  sortRow: { flexDirection: "row", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 },
  sortLabel: { fontSize: 12, color: theme.muted, fontWeight: "500" },
  sortBtn: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1.5, borderColor: theme.pink },
  sortBtnOn: { backgroundColor: theme.pink },
  sortBtnText: { fontSize: 12, fontWeight: "600", color: theme.pinkDark },
  card: { backgroundColor: "#fff", borderWidth: 1, borderColor: theme.line, borderRadius: 14, padding: 12, marginTop: 14 },
  thumb: { width: 92, height: 120, borderRadius: 10, backgroundColor: theme.pinkTint },
  cTitle: { fontWeight: "700", color: theme.ink, fontSize: 14 },
  cBrand: { color: theme.muted, fontSize: 12 },
  cPrice: { color: theme.pinkDark, fontWeight: "800", fontSize: 15, marginVertical: 4 },
  metaRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 3 },
  metaLabel: { color: theme.muted, fontSize: 12 },
  metaValue: { color: theme.ink, fontSize: 12, fontWeight: "600" },
  statusBadge: { borderRadius: 8, paddingHorizontal: 10, paddingVertical: 2 },
  statusText: { fontSize: 11, fontWeight: "700" },
  actions: { flexDirection: "row", gap: 10, marginTop: 12 },
  viewBtn: { flex: 1, flexDirection: "row", justifyContent: "center", alignItems: "center", borderWidth: 1.5, borderColor: theme.pink, borderRadius: 9, paddingVertical: 9 },
  viewText: { color: theme.pink, fontWeight: "700", fontSize: 12.5 },
  confirmBtn: { flexDirection: "row", justifyContent: "center", alignItems: "center", backgroundColor: "#1f8a4c", borderRadius: 9, paddingVertical: 9 },
  cancelBtn: { flexDirection: "row", justifyContent: "center", alignItems: "center", backgroundColor: "#c0392b", borderRadius: 9, paddingVertical: 9 },
  trackBtn: { flex: 1, flexDirection: "row", justifyContent: "center", alignItems: "center", backgroundColor: theme.pink, borderRadius: 9, paddingVertical: 9 },
  trackText: { color: "#fff", fontWeight: "700", fontSize: 12.5 },
  secure: { flexDirection: "row", alignItems: "center", backgroundColor: theme.pinkTint, borderRadius: 12, padding: 14, marginTop: 16 },
  secureText: { color: "#5b5360", fontSize: 13 },
  empty: { alignItems: "center", padding: 40 },
  emptyText: { color: theme.muted, marginTop: 10 },
});
