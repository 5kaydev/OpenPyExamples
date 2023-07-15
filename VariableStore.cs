using System.Text;
using System.Text.RegularExpressions;

namespace ConvertedTests.StepDefinitions
{
    public class VariableStore
    {
        private static readonly string ConcatRegex = @"~concat\[\[(.*)\]\]";

        private static readonly string DateFunctionRegex =
            @"~(dw|lastmonthw|lastweekw|lastyearw|mw|nextmonthw|nextweekw|nextyearw|thisyearw|todayw|tomorroww|yesterdayw|yw|workingdays|d|lastmonth|lastweek|lastyear|m|nextmonth|nextweek|nextyear|thisyear|today|tomorrow|yesterday|y)([+-]?\d+)?({(.*?)})?";

        private static readonly string GetDateRegex = @"#getdate\(\s*([+-]?\d+)\s*\)";

        private static readonly string GetKeyRegex = @"~getkey\(([^,]*),(.*?)\)";

        private static readonly string GetTimeRegex = @"#gettime\((.*)\)";

        private static readonly string RandomRegex = @"~random{([^{}]*)}";

        private static readonly string RandomizeRegex = @"~randomize{(\d+)(\s*,\s*(\d+))?[^}]*}";

        private static readonly string ReplaceRegex = @"~replace\s*\(\s*([^~]*)\s*,\s*""(.*)""\s*,\s*""(.*)""\s*\)";

        private static readonly string Substring1Regex = @"~substring\s*\(\s*({[^}]*})\s*,\s*(\d+)\s*\)";

        private static readonly string Substring2Regex = @"~substring\s*\(\s*({[^}]*})\s*,\s*(\d+)\s*,\s*(\d+)\s*\)";

        private static readonly string VariableLookupRegex = "({[^:{}]*})";

        private static readonly Dictionary<string, Func<DateTime, int, DateTime>> DateFunctions =
            new()
            {
                { "d", (now, delta) => now.AddDays(delta) },
                { "dw", (now, delta) => GetWeekDay(now.AddDays(delta)) },
                { "lastmonth", (now, delta) => now.AddMonths(delta - 1) },
                { "lastmonthw", (now, delta) => GetWeekDay(now.AddMonths(delta - 1)) },
                { "lastweek", (now, delta) => now.AddMonths(delta - 7) },
                { "lastweekw", (now, delta) => GetWeekDay(now.AddDays(delta - 7)) },
                { "lastyear", (now, delta) => now.AddYears(delta - 1) },
                { "lastyearw", (now, delta) => GetWeekDay(now.AddYears(delta - 1)) },
                { "m", (now, delta) => now.AddMonths(delta) },
                { "mw", (now, delta) => GetWeekDay(now.AddMonths(delta)) },
                { "nextmonth", (now, delta) => now.AddMonths(delta + 1) },
                { "nextmonthw", (now, delta) => GetWeekDay(now.AddMonths(delta + 1)) },
                { "nextweek", (now, delta) => now.AddMonths(delta + 7) },
                { "nextweekw", (now, delta) => GetWeekDay(now.AddDays(delta + 7)) },
                { "nextyear", (now, delta) => now.AddYears(delta + 1) },
                { "nextyearw", (now, delta) => GetWeekDay(now.AddYears(delta + 1)) },
                { "thisyear", (now, delta) => now.AddYears(delta) },
                { "thisyearw", (now, delta) => GetWeekDay(now.AddYears(delta)) },
                { "today", (now, delta) => now.AddDays(delta) },
                { "todayw", (now, delta) => GetWeekDay(now.AddDays(delta)) },
                { "tomorrow", (now, delta) => now.AddDays(delta + 1) },
                { "tomorroww", (now, delta) => GetWeekDay(now.AddDays(delta + 1)) },
                { "workingdays", (now, delta) => AddWorkingDays(now, delta) },
                { "y", (now, delta) => now.AddYears(delta) },
                { "yw", (now, delta) => GetWeekDay(now.AddYears(delta)) },
                { "yesterday", (now, delta) => now.AddDays(delta - 1) },
                { "yesterdayw", (now, delta) => GetWeekDay(now.AddDays(delta - 1)) }
            };

        private static readonly Dictionary<DayOfWeek, int> WorkingDayDecrements = new()
        {
            { DayOfWeek.Monday, 3 },
            { DayOfWeek.Tuesday, 1 },
            { DayOfWeek.Wednesday, 1 },
            { DayOfWeek.Thursday, 1 },
            { DayOfWeek.Friday, 1 },
            { DayOfWeek.Saturday, 1 },
            { DayOfWeek.Sunday, 2 }
        };

        private static readonly Dictionary<DayOfWeek, int> WorkingDayIncrements = new()
        {
            { DayOfWeek.Monday, 1 },
            { DayOfWeek.Tuesday, 1 },
            { DayOfWeek.Wednesday, 1 },
            { DayOfWeek.Thursday, 1 },
            { DayOfWeek.Friday, 3 },
            { DayOfWeek.Saturday, 2 },
            { DayOfWeek.Sunday, 1 }
        };

        private readonly Random _random = new();
        private readonly Dictionary<string, string> _variables = new();

        private static DateTime AddWorkingDays(DateTime date, int delta)
        {
            if (delta == 0)
            {
                return date;
            }
            if (delta > 0)
            {
                for (var i = 0; i < delta; i++)
                {
                    date = date.AddDays(WorkingDayIncrements[date.DayOfWeek]);
                }
            }
            else
            {
                for (var i = 0; i < -delta; i++)
                {
                    date = date.AddDays(-WorkingDayDecrements[date.DayOfWeek]);
                }
            }
            return date;
        }

        private static string GetDate(string functionName, int delta, string format)
        {
            return DateFunctions[functionName](DateTime.UtcNow, delta).ToString(format);
        }

        private static DateTime GetWeekDay(DateTime date)
        {
            while (date.DayOfWeek == DayOfWeek.Sunday || date.DayOfWeek == DayOfWeek.Saturday)
            {
                date = date.AddDays(1);
            }
            return date;
        }

        private void AddOrReplaceVariable(string key, string value)
        {
            _variables[key] = value;
        }

        private string GenerateValue(string format)
        {
            if ("NNNN-NN-NNTNN:NN:NN".Equals(format))
            {
                return DateTime.Now.Date.AddYears(_random.Next(-30, -20)).ToString("yyyy-MM-dd'T'HH:mm:ss");
            }
            format = format.Replace("&amp;", "").Replace("&lt;", "").Replace("&gt;", "");
            var builder = new StringBuilder();
            var charsets = new Dictionary<char, string>
            {
                { 'A', "ABCDEFGHIJKLMNOPQRSTUVWXYZ" },
                { 'a', "abcdefghijklmnopqrstuvwxyz" },
                { 'N', "0123456789" }
            };
            foreach (var c in format)
            {
                var nextChar = charsets.ContainsKey(c) ? GetRandomChar(charsets[c]) : c;
                builder.Append(nextChar);
            }
            return builder.ToString();
        }

        private char GetRandomChar(string charset)
        {
            return charset[_random.Next(0, charset.Length)];
        }

        private string GetRandomNumberDigits(int minLength, int maxLength, bool leadingZero = true)
        {
            if (minLength == 0 && maxLength == 0)
            {
                return "";
            }
            var length = _random.Next(minLength, maxLength);
            var builder = new StringBuilder();
            builder.Append(GetRandomChar(leadingZero ? "0123456789" : "23456789"));
            for (var i = 1; i < length; i++)
            {
                builder.Append(GetRandomChar("0123456789"));
            }
            return builder.ToString();
        }

        private string GetRandomName(int minLength, int maxLength)
        {
            var builder = new StringBuilder();
            var length = _random.Next(minLength, maxLength);
            for (var i = 0; i < length; i++)
            {
                builder.Append(GetRandomChar("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"));
            }
            return builder.ToString();
        }

        private string ProcessConcat(Match match)
        {
            var expression = match.Groups[1].Value.Replace('&', '+');
            var result = string.Empty;
            foreach (var term in expression.Split('+'))
            {
                if (term.ToLower().Contains("text(now()"))
                {
                    var regexp = new Regex(@"text\(now\(\).*?""(.*?)""", RegexOptions.IgnoreCase);
                    match = regexp.Match(term);
                    if (match.Success)
                    {
                        var format = match.Groups[1].Value.Replace("Y", "y").Replace("D", "d");
                        result = result + DateTime.UtcNow.ToString(format);
                    }
                    else
                    {
                        throw new Exception($"Missing format in text(now() expression {match.Groups[0].Value}");
                    }
                }
                else
                {
                    result = result + term.Replace("\"", string.Empty);
                }
            }
            return result;
        }

        private string ProcessDateFunctions(Match match)
        {
            var functionName = match.Groups[1].Value.ToLower();
            var deltaGroup = match.Groups[2].Value;
            var delta = 0;
            if (!string.IsNullOrWhiteSpace(deltaGroup) && !int.TryParse(deltaGroup, out delta))
            {
                throw new Exception($"Unparsable index {deltaGroup} in date expression");
            }
            var formatGroup = match.Groups[4].Value;
            var format = string.IsNullOrWhiteSpace(formatGroup) ? "MM/dd/yyyy" : formatGroup.Trim();
            return GetDate(functionName, delta, format);
        }

        private string ProcessGetDate(Match match)
        {
            var delta = int.Parse(match.Groups[1].Value);
            return GetDate("today", delta, "MM/dd/yyyy");
        }

        private string ProcessGetKey(Match match)
        {
            var key = match.Groups[1].Value.ToLower();
            key = key.StartsWith("{") ? key : "{" + key;
            key = key.EndsWith("}") ? key : key + "}";
            var format = match.Groups[2].Value.Replace(",", "");
            var value = GenerateValue(format);
            AddOrReplaceVariable(key, value);
            Console.WriteLine($"key = {key} value = {value}");
            return value;
        }

        private string ProcessGetTime(Match match)
        {
            var code = match.Groups[1].Value;
            var date = code.Contains("-1") ? DateTime.UtcNow.AddHours(-1) : DateTime.UtcNow;
            return date.ToString("HH:mm:ss");
        }

        private string ProcessRandom(Match match)
        {
            var format = match.Groups[1].Value;
            var builder = new StringBuilder();
            foreach (var c in format)
            {
                var charset = c switch
                {
                    _ when char.IsDigit(c) => builder.Length == 0 ? "123456789" : "0123456789",
                    _ when char.IsLower(c) => "abcdefghijklmnopqrstuvwxyz",
                    _ when char.IsUpper(c) => "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                    _ => null
                };
                var nextChar = charset != null ? charset.Substring(_random.Next(0, charset.Length), 1)[0] : c;
                builder.Append(nextChar);
            }
            return builder.ToString();
        }

        private string ProcessRandomize(Match match)
        {
            var alpha = int.Parse(match.Groups[1].Value);
            var numericString = match.Groups[3].Value;
            if (string.IsNullOrWhiteSpace(numericString))
            {
                return GetRandomName(alpha, alpha);
            }
            var numeric = int.Parse(numericString);
            return alpha == 0 && numeric == 10
                ? GetRandomNumberDigits(3, 3, false) + GetRandomNumberDigits(3, 3, false) + GetRandomNumberDigits(4, 4)
                : GetRandomName(alpha, alpha) + GetRandomNumberDigits(numeric, numeric, false);
        }

        private string ProcessReplace(Match match)
        {
            var input = match.Groups[1].Value;
            var toReplace = match.Groups[2].Value;
            var replacement = match.Groups[3].Value;
            return input.Replace(toReplace, replacement);
        }

        private string ProcessSubstring1(Match match)
        {
            var variable_name = match.Groups[1].Value.ToLower();
            var start = int.Parse(match.Groups[2].Value);
            if (_variables.ContainsKey(variable_name))
            {
                return _variables[variable_name].Substring(start);
            }
            throw new Exception($"undefined variable {variable_name} in substring expression");
        }

        private string ProcessSubstring2(Match match)
        {
            var variable_name = match.Groups[1].Value.ToLower();
            var start = int.Parse(match.Groups[2].Value);
            var length = int.Parse(match.Groups[3].Value);
            if (_variables.ContainsKey(variable_name))
            {
                return _variables[variable_name].Substring(start, length);
            }
            throw new Exception($"undefined variable {variable_name} in substring expression");
        }

        private string ProcessVariableLookup(Match match)
        {
            var key = match.Groups[1].Value.ToLower();
            if (_variables.ContainsKey(key))
            {
                return _variables[key];
            }
            throw new Exception($"undefined variable {key}");
        }

        public void StoreVariable(string key, string value)
        {
            AddOrReplaceVariable(key.ToLower(), value);
        }

        public string Substitute(string input)
        {
            var substitutions =
                new List<ValueTuple<Regex, Func<Match, string>>>
                {
                    (new Regex(GetKeyRegex, RegexOptions.IgnoreCase), ProcessGetKey),
                    (new Regex(ConcatRegex, RegexOptions.IgnoreCase), ProcessConcat),
                    (new Regex(DateFunctionRegex, RegexOptions.IgnoreCase), ProcessDateFunctions),
                    (new Regex(GetDateRegex, RegexOptions.IgnoreCase), ProcessGetDate),
                    (new Regex(GetTimeRegex, RegexOptions.IgnoreCase), ProcessGetTime),
                    (new Regex(RandomRegex, RegexOptions.IgnoreCase), ProcessRandom),
                    (new Regex(RandomizeRegex, RegexOptions.IgnoreCase), ProcessRandomize),
                    (new Regex(Substring1Regex, RegexOptions.IgnoreCase), ProcessSubstring1),
                    (new Regex(Substring2Regex, RegexOptions.IgnoreCase), ProcessSubstring2),
                    (new Regex(VariableLookupRegex), ProcessVariableLookup),
                    (new Regex(ReplaceRegex, RegexOptions.IgnoreCase), ProcessReplace)
                };
            var complete = false;
            while (!complete)
            {
                complete = true;
                foreach (var substitution in substitutions)
                {
                    var result = ProcessSubstitution(substitution, input);
                    if (result.Item1)
                    {
                        input = result.Item2;
                        complete = false;
                    }
                }
            }
            return input;
        }

        private ValueTuple<bool, string> ProcessSubstitution(ValueTuple<Regex, Func<Match, string>> substitution,
            string input)
        {
            var found = false;
            var match = substitution.Item1.Match(input);
            while (match.Success)
            {
                found = true;
                var newValue = substitution.Item2(match);
                input = input.Remove(match.Index, match.Length).Insert(match.Index, newValue);
                match = substitution.Item1.Match(input);
            }
            return (found, input);
        }
    }
}