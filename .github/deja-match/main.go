// deja-match: CI check of bin/deja-scope's policy against deja's ignore rule.
// matches() is deja's own rule (internal/policy/ignore.go, deja 0.24.3): Go's path.Match on the session's path and
// project, else the pattern's literal middle as a substring. Usage: deja-match <policy.json> < cases ("project\twant").
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path"
	"strings"
)

func matches(pattern, s string) bool {
	if s == "" {
		return false
	}
	if ok, err := path.Match(pattern, s); err == nil && ok {
		return true
	}
	lit := strings.Trim(pattern, "*")
	return lit != "" && !strings.ContainsAny(lit, "*?[") && strings.Contains(s, lit)
}

func main() {
	var p struct{ Ignore []string }
	b, err := os.ReadFile(os.Args[1])
	if err == nil {
		err = json.Unmarshal(b, &p)
	}
	if err != nil {
		fmt.Println(err)
		os.Exit(2)
	}
	bad := 0
	for _, pat := range p.Ignore {
		if _, err := path.Match(pat, ""); err != nil { // a malformed glob matches nothing: it would leave nothing out
			bad++
			fmt.Printf("malformed pattern %q\n", pat)
		}
	}
	sc := bufio.NewScanner(os.Stdin)
	for sc.Scan() {
		x := strings.Split(sc.Text(), "\t")
		if len(x) != 2 {
			continue
		}
		got := false
		for _, pat := range p.Ignore {
			got = got || matches(pat, x[0])
		}
		if got != (x[1] == "out") {
			bad++
			fmt.Printf("%q: left out=%v, want %s\n", x[0], got, x[1])
		}
	}
	if bad > 0 {
		os.Exit(1)
	}
}
